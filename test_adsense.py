"""
Testes de verificação da integração com Google AdSense e rota /ads.txt.
"""

from starlette.testclient import TestClient
from app.main import app


def test_adsense_integration():
    client = TestClient(app)

    # 1. Rota /ads.txt
    res_ads = client.get("/ads.txt")
    assert res_ads.status_code == 200
    assert "google.com" in res_ads.text
    assert "pub-1653358832177043" in res_ads.text
    assert "DIRECT" in res_ads.text
    assert "f08c47fec0942fa0" in res_ads.text
    print("[PASS] Endpoint /ads.txt operacional com pub-1653358832177043!")

    # 2. Template index.html com AdSense
    res_index = client.get("/")
    assert res_index.status_code == 200
    html = res_index.text
    assert "ca-pub-1653358832177043" in html
    assert "adsense-live-mode" in html
    assert "pagead2.googlesyndication.com" in html
    assert "ad-slot-result-wrapper" in html
    assert "ad-footer-section" in html
    assert "Publicidade" in html
    assert "adsbygoogle" in html
    print("[PASS] Template index.html renderiza tags ativas (live-mode) e slots discretos.")


if __name__ == "__main__":
    test_adsense_integration()
    print("Todos os testes de AdSense passaram com sucesso!")
