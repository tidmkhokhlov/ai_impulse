from app.services.nlp_service import NLPService

def test_extract_inn():
    n = NLPService()
    assert n.extract_inn('ИНН 1234567890') == '1234567890'

def test_classify_ad():
    n = NLPService()
    assert n.classify_ad('Супер акция! РЕКЛАМА: скидка 50%')['is_ad'] is True
