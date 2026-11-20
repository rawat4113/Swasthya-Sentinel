import httpx

BASE='https://api.openaq.org/v3'

def fetch_nearby_particulates(latitude:float, longitude:float, api_key:str, radius:int=25000):
    """Fetch latest PM2.5/PM10 measurements near a point. Values remain concentrations, not AQI."""
    if not api_key: return {'status':'not_configured','message':'Set OPENAQ_API_KEY to enable OpenAQ.'}
    headers={'X-API-Key':api_key}
    with httpx.Client(timeout=15,headers=headers) as client:
        loc=client.get(f'{BASE}/locations',params={'coordinates':f'{latitude:.4f},{longitude:.4f}','radius':min(radius,25000),'limit':10})
        loc.raise_for_status(); locations=loc.json().get('results',[])
        readings={'pm25':None,'pm10':None,'station_name':None,'observed_at':None}
        for location in locations:
            lid=location.get('id')
            if not lid: continue
            sensors_resp=client.get(f'{BASE}/locations/{lid}/sensors')
            sensors_resp.raise_for_status()
            sensor_map={}
            for sensor in sensors_resp.json().get('results',[]):
                param=sensor.get('parameter') or {}; name=(param.get('name') or '').lower().replace('.','').replace('_','').replace(' ','')
                target='pm25' if name in ('pm25','pm25') else ('pm10' if name=='pm10' else None)
                if target and sensor.get('id'): sensor_map[int(sensor['id'])]=target
            if not sensor_map: continue
            latest=client.get(f'{BASE}/locations/{lid}/latest',params={'limit':100})
            latest.raise_for_status()
            for item in latest.json().get('results',[]):
                sid=item.get('sensorsId') or item.get('sensors_id')
                target=sensor_map.get(int(sid)) if sid is not None else None
                if not target or readings[target] is not None: continue
                readings[target]=item.get('value')
                dt=item.get('datetime') or {}
                readings['observed_at']=dt.get('utc') or readings['observed_at']
                readings['station_name']=location.get('name')
            if readings['pm25'] is not None and readings['pm10'] is not None: break
        if readings['pm25'] is None and readings['pm10'] is None:
            return {'status':'no_measurements','message':'No nearby PM2.5/PM10 measurements were returned.'}
        return {'status':'success',**readings}
