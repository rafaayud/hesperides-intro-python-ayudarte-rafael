"""
Backtest de optimización para la estrategia de cruce de medias (MeanCross).

FOCO: Encontrar el Take Profit óptimo usando multiprocessing y numpy.

Genera un reporte comparativo con las mejores configuraciones de TP.
"""
import asyncio
import logging
from time import perf_counter
from typing import List, Dict, Tuple, NamedTuple
from decimal import Decimal
import numpy as np
from multiprocessing import Pool, cpu_count
from dataclasses import dataclass

from modules.trading.application.services.backtest_service import BacktestService
from modules.trading.domain.value_objects import Symbol, Interval, Candle_static
from modules.trading.domain.strategies.mean_cross_backtest import MeanCrossBacktest

from modules.trading.infrastructure.postgre_adapter import PostgresAdapter
from modules.trading.infrastructure.binance_adapter import BinanceAdapter


from modules.trading.domain.aggregates.backtest_result import BacktestResult
from modules.trading.application.services.ingestion_service import DataIngestionService
from modules.trading.domain.strategies.base import Strategy

from modules.trading.domain.utils import timed_async, timed


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACIÓN GLOBAL PARA MULTIPROCESSING
# ============================================================================
DB_URL = "postgresql://postgres:1234@localhost:5432/postgres"

# Variable global para compartir candles con los workers
_SHARED_CANDLES: List[Candle_static] = []


@dataclass
class BacktestConfig:
    """Configuración serializable para un backtest."""
    fast_period: int
    slow_period: int
    take_profit: float  # Porcentaje (ej: 0.02 = 2%)
    interval: Interval
    symbol_str: str
    initial_capital: float = 10000.0


def _init_worker(candles: List[Candle_static]) -> None:
    """Inicializa el worker con los candles compartidos."""
    global _SHARED_CANDLES
    _SHARED_CANDLES = candles


def run_single_backtest(config: BacktestConfig) -> Dict:
    """
    Ejecuta un backtest individual usando los candles compartidos.
    No necesita conexión a DB.
    """
    global _SHARED_CANDLES
    
    try:
        # Crear estrategia
        tp_config = {config.interval: config.take_profit}
        strategy = MeanCrossBacktest(
            slow_period=config.slow_period,
            fast_period=config.fast_period,
            take_profit=tp_config
        )
        
        if len(_SHARED_CANDLES) < strategy.min_candles_required:
            return {
                'config': config,
                'error': f'Not enough candles: {len(_SHARED_CANDLES)} < {strategy.min_candles_required}',
                'pnl': 0,
                'pnl_pct': 0,
                'trades': 0,
                'win_rate': 0,
                'final_capital': config.initial_capital
            }
        
        # Ejecutar backtest (BacktestService con storage=None, solo usamos test_strategy)
        backtest_service = BacktestService(storage=None)
        result = backtest_service.test_strategy(strategy, _SHARED_CANDLES, config.initial_capital)
        
        # Debug: verificar resultado
        pnl = float(result.total_pnl.value) if hasattr(result.total_pnl, 'value') else float(result.total_pnl)
        avg_pnl = 0
        if result.total_trades > 0:
            avg_pnl = float(result.avg_pnl_per_trade.value) if hasattr(result.avg_pnl_per_trade, 'value') else float(result.avg_pnl_per_trade)
        
        return {
            'config': config,
            'pnl': pnl,
            'pnl_pct': result.total_pnl_percentage,
            'trades': result.total_trades,
            'win_rate': result.win_rate,
            'winners': result.total_winners,
            'losers': result.total_losers,
            'final_capital': result.final_capital,
            'avg_pnl_per_trade': avg_pnl
        }
        
    except Exception as e:
        import traceback
        print(f"❌ Error in backtest (fast={config.fast_period}, slow={config.slow_period}, tp={config.take_profit}): {e}")
        traceback.print_exc()
        return {
            'config': config,
            'error': str(e),
            'pnl': 0,
            'pnl_pct': 0,
            'trades': 0,
            'win_rate': 0,
            'final_capital': config.initial_capital
        }


class TakeProfitOptimizer:
    """Optimizador enfocado en encontrar el Take Profit óptimo."""
    
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        interval: Interval = Interval.H1,
        # Medias fijas o a probar
        fast_periods: np.ndarray = None,
        slow_periods: np.ndarray = None,
        # Rango de Take Profits a testear (lo importante!)
        tp_min: float = 0.005,   # 0.5%
        tp_max: float = 0.10,    # 10%
        tp_steps: int = 15,      # Número de TPs a probar
        initial_capital: float = 10000.0
    ):
        self.symbol = symbol
        self.interval = interval
        self.initial_capital = initial_capital
        
        # Períodos de medias (por defecto algunos valores razonables)
        self.fast_periods = fast_periods if fast_periods is not None else np.array([10, 20])
        self.slow_periods = slow_periods if slow_periods is not None else np.array([50, 100])
        
        # Generar grid de Take Profits con numpy
        self.take_profits = np.linspace(tp_min, tp_max, tp_steps)

        # Candles cargados una sola vez
        self.candles: List[Candle_static] = []
        
        self.results: List[Dict] = []
    
    def generate_configs(self) -> List[BacktestConfig]:
        """Genera todas las configuraciones a testear usando numpy meshgrid."""
        configs = []
        
        # Crear meshgrid de todas las combinaciones
        for fast in self.fast_periods:
            for slow in self.slow_periods:
                if fast >= slow:
                    continue  # Fast debe ser menor que slow
                    
                for tp in self.take_profits:
                    configs.append(BacktestConfig(
                        fast_period=int(fast),
                        slow_period=int(slow),
                        take_profit=float(tp),
                        interval=self.interval,
                        symbol_str=self.symbol,
                        initial_capital=self.initial_capital
                    ))
        
        return configs

    async def load_candles(self) -> None:
        """Carga los candles UNA SOLA VEZ antes del multiprocessing."""
        storage = PostgresAdapter(DB_URL)
        await storage.connect()
        self.candles = await storage.get_candles(
            Symbol(self.symbol), 
            self.interval, 
            self.interval.max_candles
        )
        await storage.disconnect()
        print(f"📊 Loaded {len(self.candles)} candles for {self.symbol} [{self.interval.value}]")
    
    def run_optimization(self, n_processes: int = None) -> List[Dict]:
        """Ejecuta todos los backtests en paralelo."""
        if not self.candles:
            raise ValueError("No candles loaded. Call load_candles() first.")
        
        configs = self.generate_configs()
        n_processes = n_processes or cpu_count()
        
        print("\n" + "="*80)
        print("BACKTEST OPTIMIZATION")
        print("="*80)
        print(f"   Symbol:          {self.symbol}")
        print(f"   Interval:        {self.interval.value}")
        print(f"   Candles:         {len(self.candles)}")
        print(f"   Fast periods:    {self.fast_periods.tolist()}")
        print(f"   Slow periods:    {self.slow_periods.tolist()}")
        print(f"   Take Profits:    {len(self.take_profits)} values ({self.take_profits[0]*100:.1f}% - {self.take_profits[-1]*100:.1f}%)")
        print(f"   Total configs:   {len(configs)}")
        print(f"   Processes:       {n_processes}")
        print("="*80 + "\n")
        
        start_time = perf_counter()
        
        # Ejecutar en paralelo con initializer para compartir candles
        with Pool(processes=n_processes, initializer=_init_worker, initargs=(self.candles,)) as pool:
            self.results = pool.map(run_single_backtest, configs)
        
        elapsed = perf_counter() - start_time
        print(f" Completed in {elapsed:.2f}s ({len(configs)/elapsed:.1f} backtests/s)\n")
        
        return self.results
    
    def analyze_by_take_profit(self) -> None:
        """Analiza resultados agrupados por Take Profit."""
        if not self.results:
            print("❌ No results. Execute run_optimization() first.")
            return
        
        # Filtrar errores
        valid_results = [r for r in self.results if 'error' not in r]
        
        if not valid_results:
            print(" All backtests failed.")
            return
        
        tp_groups: Dict[float, List[Dict]] = {}
        for r in valid_results:
            tp = r['config'].take_profit
            if tp not in tp_groups:
                tp_groups[tp] = []
            tp_groups[tp].append(r)
        
        # Calcular métricas por TP usando numpy
        print("\n" + "="*100)
        print("📊 ANALYSIS BY TAKE PROFIT")
        print("="*100)
        print(f"{'TP %':<8} {'PnL Mean':<12} {'PnL Median':<12} {'Win Rate':<10} {'Trades':<8} {'Profitable':<10} {'Best PnL':<12}")
        print("-"*100)
        
        tp_stats = []
        for tp in sorted(tp_groups.keys()):
            group = tp_groups[tp]
            pnls = np.array([r['pnl'] for r in group])
            win_rates = np.array([r['win_rate'] for r in group])
            trades = np.array([r['trades'] for r in group])
            
            profitable = np.sum(pnls > 0)
            
            stats = {
                'tp': tp,
                'pnl_mean': pnls.mean(),
                'pnl_median': np.median(pnls),
                'pnl_std': pnls.std(),
                'pnl_max': pnls.max(),
                'pnl_min': pnls.min(),
                'win_rate_mean': win_rates.mean(),
                'trades_mean': trades.mean(),
                'profitable_count': profitable,
                'total_count': len(group)
            }
            tp_stats.append(stats)
            
            print(
                f"{tp*100:>6.2f}% "
                f"${stats['pnl_mean']:>10,.2f} "
                f"${stats['pnl_median']:>10,.2f} "
                f"{stats['win_rate_mean']:>8.1f}% "
                f"{stats['trades_mean']:>6.0f} "
                f"{profitable}/{len(group):<5} "
                f"${stats['pnl_max']:>10,.2f}"
            )
        
        print("="*100)
        
        # Encontrar TP óptimo
        best_by_pnl = max(tp_stats, key=lambda x: x['pnl_mean'])
        best_by_winrate = max(tp_stats, key=lambda x: x['win_rate_mean'])
        best_by_consistency = max(tp_stats, key=lambda x: x['pnl_median'])
        
        print("\n" + "🏆 OPTIMAL TAKE PROFIT:")
        print(f"   By PnL Mean:      {best_by_pnl['tp']*100:.2f}% (${best_by_pnl['pnl_mean']:,.2f})")
        print(f"   By Win Rate:       {best_by_winrate['tp']*100:.2f}% ({best_by_winrate['win_rate_mean']:.1f}%)")
        print(f"   By Consistency:   {best_by_consistency['tp']*100:.2f}% (median: ${best_by_consistency['pnl_median']:,.2f})")
    
    def analyze_top_configs(self, top_n: int = 15) -> None:
        """Muestra las mejores configuraciones individuales."""
        if not self.results:
            print("❌ No results.")
            return
        
        valid_results = [r for r in self.results if 'error' not in r]
        sorted_results = sorted(valid_results, key=lambda x: x['pnl'], reverse=True)
        
        print("\n" + "="*110)
        print(f" TOP {top_n} BEST CONFIGURATIONS")
        print("="*110)
        print(f"{'#':<4} {'Fast':<6} {'Slow':<6} {'TP %':<8} {'PnL':<14} {'PnL %':<10} {'Trades':<8} {'Winners/Losers':<10} {'Win Rate':<10}")
        print("-"*110)
        
        for i, r in enumerate(sorted_results[:top_n], 1):
            cfg = r['config']
            print(
                f"{i:<4} "
                f"{cfg.fast_period:<6} "
                f"{cfg.slow_period:<6} "
                f"{cfg.take_profit*100:>5.2f}%  "
                f"${r['pnl']:>12,.2f} "
                f"{r['pnl_pct']:>+8.2f}% "
                f"{r['trades']:<8} "
                f"{r['winners']}/{r['losers']:<6} "
                f"{r['win_rate']:>7.1f}%"
            )
        
        print("="*110)
    
    def get_optimal_config(self) -> Dict:
        """Retorna la mejor configuración encontrada."""
        valid_results = [r for r in self.results if 'error' not in r]
        return max(valid_results, key=lambda x: x['pnl'])


async def sync_historical_data(symbol: str, intervals: List[Interval]) -> None:
    """Sincroniza datos históricos antes del backtest."""
    storage = PostgresAdapter(DB_URL)
    binance = BinanceAdapter()
    ingestion = DataIngestionService(storage, binance)
    
    async with ingestion as ing:
            logger.info(f" Synchronizing {symbol}...")
            await ing.sync_all([Symbol(symbol)], intervals)


async def main():
    """Main con diferentes casos de uso."""
    
    print("\n" + "#"*40)
    print("   BACKTEST OPTIMIZATION OF TAKE PROFIT")
    print("#"*40 + "\n")
    
    # =========================================================================
    # CONFIGURACIÓN - AJUSTA ESTOS VALORES
    # =========================================================================
    
    SYMBOL = "BTCUSDT"
    # INTERVAL = Interval.H1
    INTERVAL = Interval.M1
    

    
    # Períodos de medias a testear
    FAST_PERIODS = np.array([5, 10, 15])
    SLOW_PERIODS = np.array([30, 50, 100])
    
    # Rango de Take Profits a testear (¡LO MÁS IMPORTANTE!)
    TP_MIN = 0.005    # 0.5%
    TP_MAX = 0.08     # 8%
    TP_STEPS = 16     # Número de valores a probar
    
    INITIAL_CAPITAL = 10000.0
    
    # =========================================================================
    # EJECUCIÓN
    # =========================================================================
    
    print("Synchronizing historical data...")
    await sync_historical_data(SYMBOL, [INTERVAL])
    
    optimizer = TakeProfitOptimizer(
        symbol=SYMBOL,
        interval=INTERVAL,
        fast_periods=FAST_PERIODS,
        slow_periods=SLOW_PERIODS,
        tp_min=TP_MIN,
        tp_max=TP_MAX,
        tp_steps=TP_STEPS,
        initial_capital=INITIAL_CAPITAL
    )
    
    await optimizer.load_candles()
    
    optimizer.run_optimization()
    
    optimizer.analyze_by_take_profit() 
    optimizer.analyze_top_configs(top_n=15)
    
    best = optimizer.get_optimal_config()
    cfg = best['config']
    
    print("\n" + "="*60)
    print("🎯 OPTIMAL CONFIGURATION FOUND:")
    print("="*60)
    print(f"   Fast Period:     {cfg.fast_period}")
    print(f"   Slow Period:     {cfg.slow_period}")
    print(f"   Take Profit:     {cfg.take_profit*100:.2f}%")
    print(f"   PnL:             ${best['pnl']:,.2f} ({best['pnl_pct']:+.2f}%)")
    print(f"   Trades:          {best['trades']} ({best['winners']}W / {best['losers']}L)")
    print(f"   Win Rate:        {best['win_rate']:.1f}%")
    print(f"   Capital Final:   ${best['final_capital']:,.2f}")
    print("="*60 + "\n")


if __name__ == "__main__":
    start = perf_counter()
    asyncio.run(main())
    print(f"Total time: {perf_counter() - start:.2f}s")

