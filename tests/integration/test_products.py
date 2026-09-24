from uuid import uuid4

import httpx


def create_org(client, headers, name):
    return client.post(
        "/v1/organizations",
        headers={**headers, "Idempotency-Key": str(uuid4())},
        json={"name": name},
    ).json()["id"]


def test_manager_keeps_exact_zero_and_unknown_prices(client, identity):
    _, headers = identity()
    org = create_org(client, headers, "Alfa")
    base = f"/v1/orgs/{org}/products"

    zero = client.post(base, headers=headers, json={
        "name": "Consulta", "price": "0.0000", "available": True,
    })
    assert zero.status_code == 201
    assert zero.json()["price"] == "0.0000"
    assert zero.json()["commercialRevision"] == 2

    unknown = client.post(base, headers=headers, json={
        "name": "Projeto", "price": None, "available": False,
    })
    assert unknown.status_code == 201
    catalog = client.get(base, headers=headers)
    assert catalog.status_code == 200
    assert catalog.json()["commercialRevision"] == 3
    assert [(p["name"], p["price"], p["available"]) for p in catalog.json()["products"]] == [
        ("Consulta", "0.0000", True), ("Projeto", None, False),
    ]


def test_correction_preserves_prior_version_and_rejects_stale_edit(client, identity):
    _, headers = identity()
    org = create_org(client, headers, "Alfa")
    base = f"/v1/orgs/{org}/products"
    original = client.post(base, headers=headers, json={
        "name": "Plano", "price": "123.4567", "available": True,
    }).json()
    path = f"{base}/{original['id']}"

    changed = client.put(path, headers=headers, json={
        "version": 1, "name": "Plano revisado", "price": "120.0001", "available": False,
    })
    assert changed.status_code == 200
    assert changed.json()["version"] == 2
    assert changed.json()["commercialRevision"] == 3
    assert changed.json()["price"] == "120.0001"
    stale = client.put(path, headers=headers, json={
        "version": 1, "name": "Edição antiga", "price": "1", "available": True,
    })
    assert stale.status_code == 409
    assert client.get(base, headers=headers).json()["commercialRevision"] == 3
    versions = client.get(path + "/versions", headers=headers)
    assert versions.status_code == 200
    assert [(p["name"], p["price"], p["available"], p["commercialRevision"])
            for p in versions.json()] == [
        ("Plano", "123.4567", True, 2),
        ("Plano revisado", "120.0001", False, 3),
    ]


def test_other_company_and_seller_cannot_change_catalog(client, identity):
    _, alpha = identity()
    _, beta = identity()
    alpha_org = create_org(client, alpha, "Alfa")
    beta_org = create_org(client, beta, "Beta")
    alpha_base = f"/v1/orgs/{alpha_org}/products"
    beta_base = f"/v1/orgs/{beta_org}/products"
    product = client.post(beta_base, headers=beta, json={
        "name": "Segredo Beta", "price": "5.0000", "available": True,
    }).json()
    assert client.get(beta_base, headers=alpha).status_code == 404
    assert client.get(alpha_base, headers=alpha).json()["products"] == []
    assert client.get(f"{beta_base}/{product['id']}/versions", headers=alpha).status_code == 404
    assert client.put(f"{beta_base}/{product['id']}", headers=alpha, json={
        "version": 1, "name": "Invadir", "price": "1", "available": True,
    }).status_code == 404

    email = f"seller-{uuid4().hex}@example.test"
    seller = client.post(alpha_base.replace("products", "sellers"), headers=alpha, json={
        "name": "Bia", "email": email, "phone": "+5511999990000", "available": True,
    }).json()
    enabled = client.post(f"/v1/orgs/{alpha_org}/sellers/{seller['id']}/enable",
                          headers=alpha).json()
    login = httpx.post("http://127.0.0.1:54321/token?grant_type=password", json={
        "email": email, "password": enabled["temporary_password"],
    })
    assert login.status_code == 200
    seller_headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.post(alpha_base, headers=seller_headers, json={
        "name": "Negado", "price": None, "available": True,
    }).status_code == 404
    assert client.get(alpha_base, headers=seller_headers).status_code == 404
    assert client.get(alpha_base, headers=alpha).json()["products"] == []


def test_revocation_hides_current_product_and_preserves_versions(client, identity):
    _, headers = identity()
    org = create_org(client, headers, "Alfa")
    base = f"/v1/orgs/{org}/products"
    product = client.post(base, headers=headers, json={
        "name": "Consulta", "price": "20.2500", "available": True,
    }).json()
    path = f"{base}/{product['id']}"
    removed = client.post(path + "/revoke", headers=headers, json={"version": 1})
    assert removed.status_code == 200
    assert removed.json()["status"] == "revoked"
    assert removed.json()["commercialRevision"] == 3
    assert client.get(base, headers=headers).json() == {"commercialRevision": 3, "products": []}
    assert [v["status"] for v in client.get(path + "/versions", headers=headers).json()] == [
        "ready", "revoked",
    ]
    assert client.post(path + "/revoke", headers=headers, json={"version": 1}).status_code == 409
    assert client.get(base, headers=headers).json()["commercialRevision"] == 3


def test_invalid_price_is_rejected_without_changing_catalog(client, identity):
    _, headers = identity()
    org = create_org(client, headers, "Alfa")
    base = f"/v1/orgs/{org}/products"
    for price in ["-1", "1.00001", "10000000000000000", 1.2]:
        response = client.post(base, headers=headers, json={
            "name": "Inválido", "price": price, "available": True,
        })
        assert response.status_code == 422
    assert client.get(base, headers=headers).json() == {"commercialRevision": 1, "products": []}
