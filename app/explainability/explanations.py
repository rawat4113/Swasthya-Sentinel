def explain_contributions(risk_type, evidence):
    names={'environmental_score':'Environmental signal','clinical_score':'Health-service signal','workforce_score':'Workforce signal'}
    return [{'signal':names[k],'contribution':round(float(evidence.get(k,0))*w,1)}
            for k,w in [('environmental_score',.40),('clinical_score',.35),('workforce_score',.25)]]
