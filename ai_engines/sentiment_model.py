"""
Sentiment helpers using VADER and TextBlob.
Optional: If transformers is installed and you want better accuracy, you can plug a RoBERTa sentiment pipeline.
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
import logging

_ANALYZER = None

def _get_vader():
    global _ANALYZER
    if _ANALYZER is None:
        _ANALYZER = SentimentIntensityAnalyzer()
    return _ANALYZER

def analyze_sentiment(text: str):
    """
    Returns a dict: {
      "vader_compound": float,
      "polarity": float (TextBlob polarity -1..1),
      "subjectivity": float (0..1)
    }
    """
    if not text:
        return {"vader_compound": 0.0, "polarity": 0.0, "subjectivity": 0.0}
    vader = _get_vader()
    try:
        v = vader.polarity_scores(text)
    except Exception as e:
        logging.exception("VADER failure")
        v = {"compound": 0.0}
    try:
        tb = TextBlob(text)
        polarity = round(tb.sentiment.polarity, 4)
        subjectivity = round(tb.sentiment.subjectivity, 4)
    except Exception:
        polarity, subjectivity = 0.0, 0.0
    return {"vader_compound": round(v.get("compound", 0.0), 4), "polarity": polarity, "subjectivity": subjectivity}
