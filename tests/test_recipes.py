"""Recipe CRUD tests."""


def test_create_recipe(client, auth_headers):
    response = client.post("/recipes/", json={
        "title": "Tacos al Pastor",
        "description": "Classic Mexican recipe",
        "prep_time": 30,
        "cook_time": 45,
        "servings": 4,
        "ingredients": [
            {"text": "1 kg of pork", "order_index": 0},
            {"text": "4 tortillas", "order_index": 1},
        ],
        "steps": [
            {"text": "Marinate the meat", "order_index": 0},
            {"text": "Cook over charcoal", "order_index": 1},
        ],
    }, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Tacos al Pastor"
    assert data["slug"] == "tacos-al-pastor"
    assert len(data["ingredients"]) == 2
    assert len(data["steps"]) == 2


def test_get_recipes(client, auth_headers):
    # Create a recipe first
    client.post("/recipes/", json={
        "title": "Caesar Salad",
        "servings": 2,
    }, headers=auth_headers)

    response = client.get("/recipes/", headers=auth_headers)
    assert response.status_code == 200
    recipes = response.json()
    assert len(recipes) >= 1
    assert any(r["title"] == "Caesar Salad" for r in recipes)


def test_created_recipe_has_slug(client, auth_headers):
    """Verify that creating a recipe generates a correct slug."""
    resp = client.post("/recipes/", json={
        "title": "Pasta Carbonara",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["slug"] == "pasta-carbonara"


def test_update_recipe(client, auth_headers):
    create_resp = client.post("/recipes/", json={
        "title": "Original",
        "servings": 2,
    }, headers=auth_headers)
    recipe_id = create_resp.json()["id"]

    update_resp = client.put(f"/recipes/{recipe_id}", json={
        "title": "Updated",
        "servings": 8,
        "rating": 5,
    }, headers=auth_headers)
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Updated"
    assert update_resp.json()["servings"] == 8
    assert update_resp.json()["rating"] == 5


def test_delete_recipe(client, auth_headers):
    create_resp = client.post("/recipes/", json={
        "title": "To Delete",
    }, headers=auth_headers)
    recipe_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/recipes/{recipe_id}", headers=auth_headers)
    assert delete_resp.status_code == 200

    # Verify that it no longer appears in the list
    list_resp = client.get("/recipes/", headers=auth_headers)
    ids = [r["id"] for r in list_resp.json()]
    assert recipe_id not in ids


def test_toggle_favorite(client, auth_headers):
    create_resp = client.post("/recipes/", json={
        "title": "Favorite",
    }, headers=auth_headers)
    recipe_id = create_resp.json()["id"]
    assert create_resp.json()["is_favorite"] is False

    toggle_resp = client.patch(f"/recipes/{recipe_id}/favorite", headers=auth_headers)
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["is_favorite"] is True

    # Toggle back
    toggle_resp2 = client.patch(f"/recipes/{recipe_id}/favorite", headers=auth_headers)
    assert toggle_resp2.json()["is_favorite"] is False


# --- Culture / cuisine ---

def test_culture_defaults_to_empty(client, auth_headers):
    resp = client.post("/recipes/", json={"title": "No Culture"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["culture"] == ""


def test_create_recipe_with_culture_is_trimmed(client, auth_headers):
    resp = client.post("/recipes/", json={
        "title": "Mole Negro",
        "culture": "  Oaxacan   Mexican ",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["culture"] == "Oaxacan Mexican"

    listed = client.get("/recipes/", headers=auth_headers).json()
    assert next(r for r in listed if r["title"] == "Mole Negro")["culture"] == "Oaxacan Mexican"


def test_culture_too_long_is_rejected(client, auth_headers):
    resp = client.post("/recipes/", json={"title": "Long", "culture": "x" * 101}, headers=auth_headers)
    assert resp.status_code == 422


def test_update_culture_set_clear_and_preserve(client, auth_headers):
    rid = client.post("/recipes/", json={"title": "Ramen", "culture": "Japanese"}, headers=auth_headers).json()["id"]

    # A client that doesn't send culture must not wipe it
    resp = client.put(f"/recipes/{rid}", json={"title": "Ramen", "servings": 2}, headers=auth_headers)
    assert resp.json()["culture"] == "Japanese"

    # Changing it works
    resp = client.put(f"/recipes/{rid}", json={"title": "Ramen", "culture": "Okinawan"}, headers=auth_headers)
    assert resp.json()["culture"] == "Okinawan"

    # An explicit empty string clears it
    resp = client.put(f"/recipes/{rid}", json={"title": "Ramen", "culture": ""}, headers=auth_headers)
    assert resp.json()["culture"] == ""


def test_culture_survives_export_and_import(client, auth_headers):
    client.post("/recipes/", json={"title": "Pad Thai", "culture": "Thai"}, headers=auth_headers)
    exported = client.get("/export/recipes", headers=auth_headers)
    assert exported.status_code == 200
    assert exported.json()["recipes"][0]["culture"] == "Thai"

    rid = client.get("/recipes/", headers=auth_headers).json()[0]["id"]
    client.delete(f"/recipes/{rid}", headers=auth_headers)

    imported = client.post(
        "/import/recipes",
        files={"file": ("recipes.json", exported.content, "application/json")},
        headers=auth_headers,
    )
    assert imported.status_code == 200
    assert imported.json()["imported"] == 1
    listed = client.get("/recipes/", headers=auth_headers).json()
    assert listed[0]["culture"] == "Thai"
