import streamlit as st, pandas as pd
import plotly.express as px
from api_client import api_get,show_error
from style import apply_style,header
data=api_get('/api/v1/overview'); zone_data=api_get('/api/v1/zones'); geo=api_get('/api/v1/zones/geojson')
if show_error(data) or show_error(zone_data) or show_error(geo): st.stop()
lookup={z['id']:z for z in zone_data}; rows=[]
for z in data.get('zones',[]):
    meta=lookup.get(z['zone_id'],{})
    rows.append({'zone_id':z['zone_id'],'zone':z['zone_name'],'latitude':meta.get('latitude'),'longitude':meta.get('longitude'),'heat':z['heat']['score'],'respiratory':z['respiratory']['score'],'confidence':min(z['heat']['confidence'],z['respiratory']['confidence'])})
df=pd.DataFrame(rows)
if len(df):
    metric=st.radio('Risk layer',['Heat risk','Respiratory risk'],horizontal=True); field='heat' if metric=='Heat risk' else 'respiratory'
    try:
        import folium
        from streamlit_folium import st_folium
        center=[float(df.latitude.mean()),float(df.longitude.mean())]
        # OpenStreetMap's standard tile layer does not require a Carto API key.
        # Carto basemaps previously displayed an 'API KEY REQUIRED' watermark.
        fmap=folium.Map(location=center,zoom_start=11,tiles='OpenStreetMap',control_scale=True)
        if isinstance(geo,dict) and geo.get('features'):
            folium.GeoJson(geo,name='Monitoring-zone GeoJSON',style_function=lambda feature:{'color':'#58a6c9','weight':2,'fillColor':'#24536b','fillOpacity':0.16},tooltip=folium.GeoJsonTooltip(fields=[k for k in ['name','zone_id'] if k in (geo['features'][0].get('properties') or {})])).add_to(fmap)
        for row in rows:
            score=row[field]; color='#d9534f' if score>=70 else ('#e4a23b' if score>=50 else ('#5a9bd4' if score>=30 else '#39a879'))
            folium.CircleMarker([row['latitude'],row['longitude']],radius=9,color=color,fill=True,fill_opacity=.9,
                tooltip=f"{row['zone']} | {metric}: {score:.1f} | confidence {row['confidence']:.0f}%").add_to(fmap)
        st_folium(fmap,use_container_width=True,height=520,returned_objects=[])
    except ImportError:
        st.info('Install streamlit-folium to enable the interactive Folium map. Showing zone points in a chart instead.')
        st.plotly_chart(px.scatter_geo(df,lat='latitude',lon='longitude',color=field,size=field,hover_name='zone',hover_data=['zone_id','confidence'],projection='natural earth',template='plotly_white',title='Illustrative monitoring-zone locations'),use_container_width=True)
    st.dataframe(df,use_container_width=True,hide_index=True)
st.caption('Default zone polygons and centroids are illustrative only, not official district boundaries. Imported GeoJSON replaces the illustrative map geometry.')
