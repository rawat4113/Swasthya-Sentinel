import json

def parse_geojson(content: bytes):
    obj=json.loads(content.decode('utf-8'))
    if obj.get('type')!='FeatureCollection' or not isinstance(obj.get('features'),list):
        raise ValueError('Expected a GeoJSON FeatureCollection')
    parsed=[]
    for i,feature in enumerate(obj['features']):
        props=feature.get('properties') or {}; geom=feature.get('geometry') or {}; coords=geom.get('coordinates') or []
        try:
            if geom.get('type')=='Point': lon,lat=coords[:2]
            else:
                ring=coords[0][0] if geom.get('type')=='MultiPolygon' else coords[0]
                lon=sum(p[0] for p in ring)/len(ring); lat=sum(p[1] for p in ring)/len(ring)
        except Exception as exc: raise ValueError(f'Feature {i+1} has invalid geometry') from exc
        parsed.append({'zone_id':str(props.get('zone_id') or props.get('id') or f'IMPORTED_ZONE_{i+1}'),
                       'name':str(props.get('name') or props.get('zone_id') or f'Imported zone {i+1}'),'latitude':lat,'longitude':lon})
    return obj,parsed
