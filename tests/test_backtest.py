from app.validation.backtest import run_synthetic_backtest

def test_backtest_returns_comparison_metrics():
    report=run_synthetic_backtest()
    assert report['event_windows']==2
    assert {'fixed','statistical','multisignal'} <= set(report['models'])
    for metrics in report['models'].values():
        assert 0<=metrics['sensitivity']<=1
        assert 0<=metrics['positive_predictive_value']<=1
        assert metrics['false_alerts_per_zone_week']>=0
