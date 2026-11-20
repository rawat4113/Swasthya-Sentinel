from app.processing.quality import validate_record

def test_invalid_zone_is_rejected():
    errors=validate_record('health',{'zone_id':'NOPE','observed_at':'2026-11-18T10:00:00','clinic_visits':2},{'ZONE_01'})
    assert 'Unknown zone_id' in errors

def test_negative_aggregated_count_is_rejected():
    errors=validate_record('workforce',{'zone_id':'ZONE_01','observed_at':'2026-11-18T10:00:00','absence_count':-2},{'ZONE_01'})
    assert any('negative' in e for e in errors)

def test_invalid_datetime_is_rejected():
    errors=validate_record('environment',{'zone_id':'ZONE_01','observed_at':'not-a-date','temperature_c':32},{'ZONE_01'})
    assert any('Invalid observed_at' in e for e in errors)
