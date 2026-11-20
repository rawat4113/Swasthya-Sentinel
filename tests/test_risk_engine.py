from app.risk_engine.scoring import robust_anomaly_score, calculate_risk, severity

def test_robust_anomaly_detects_spike():
    score,meta=robust_anomaly_score([4,5,4,5,4,5,4,5,5],20)
    assert score>50
    assert meta['sample_count']==9

def test_risk_scores_are_bounded_and_explainable():
    env={'temperature_c':42,'apparent_temperature_c':46,'humidity_pct':75,'available':True}
    health={'heat_complaints':20,'respiratory_complaints':3,'available':True}
    workforce={'heat_complaints':15,'respiratory_complaints':2,'available':True}
    history={'heat_complaints':[3,4,5,4,3,4,5,4,3,4], 'work_heat_complaints':[2,2,3,2,2,3,2,2,3,2]}
    result=calculate_risk('heat',env,health,workforce,history)
    assert 0<=result['score']<=100
    assert result['severity'] in {'Normal','Watch','Elevated','High'}
    assert 'clinical_score' in result['evidence']

def test_severity_bands():
    assert severity(10)=='Normal'
    assert severity(35)=='Watch'
    assert severity(55)=='Elevated'
    assert severity(80)=='High'

def test_missing_signal_families_reduce_confidence_not_risk_inputs():
    result=calculate_risk('heat',{'available':False,'temperature_c':None,'apparent_temperature_c':None},
                          {'available':False,'heat_complaints':None},
                          {'available':False,'heat_complaints':None},{})
    assert result['confidence']==0
    assert result['evidence']['independent_signal_families']==0
