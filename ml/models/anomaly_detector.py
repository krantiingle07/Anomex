from sklearn.ensemble import IsolationForest


def detect_anomalies(features):
    model = IsolationForest(
        n_estimators=200,
        contamination=0.1,
        random_state=42
    )

    predictions = model.fit_predict(features)
    scores = model.score_samples(features)

    return predictions, scores