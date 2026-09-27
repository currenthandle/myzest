"""Weekly calorie intake tracking tests."""
from datetime import date, timedelta


def test_create_calorie_entry(client, auth_headers):
    response = client.post("/calories/", json={
        "entry_date": "2025-12-24",
        "calories": 2100,
        "note": "Christmas Eve dinner",
    }, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["entry_date"] == "2025-12-24"
    assert data["calories"] == 2100
    assert data["note"] == "Christmas Eve dinner"


def test_create_calorie_entry_rejects_negative(client, auth_headers):
    response = client.post("/calories/", json={
        "entry_date": "2025-12-24",
        "calories": -50,
    }, headers=auth_headers)
    assert response.status_code == 400


def test_list_calorie_entries(client, auth_headers):
    client.post("/calories/", json={"entry_date": "2025-12-01", "calories": 1800}, headers=auth_headers)
    client.post("/calories/", json={"entry_date": "2025-12-02", "calories": 2000}, headers=auth_headers)

    response = client.get("/calories/", headers=auth_headers)
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) >= 2


def test_list_calorie_entries_filtered_by_date_range(client, auth_headers):
    client.post("/calories/", json={"entry_date": "2025-01-01", "calories": 1500}, headers=auth_headers)
    client.post("/calories/", json={"entry_date": "2025-06-01", "calories": 2200}, headers=auth_headers)

    response = client.get("/calories/?start_date=2025-05-01&end_date=2025-07-01", headers=auth_headers)
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) == 1
    assert entries[0]["entry_date"] == "2025-06-01"


def test_get_calorie_entry_detail(client, auth_headers):
    create_resp = client.post("/calories/", json={"entry_date": "2025-03-10", "calories": 1900}, headers=auth_headers)
    entry_id = create_resp.json()["id"]

    response = client.get(f"/calories/{entry_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["calories"] == 1900


def test_update_calorie_entry(client, auth_headers):
    create_resp = client.post("/calories/", json={"entry_date": "2025-03-10", "calories": 1900}, headers=auth_headers)
    entry_id = create_resp.json()["id"]

    update_resp = client.put(f"/calories/{entry_id}", json={
        "entry_date": "2025-03-11",
        "calories": 2050,
        "note": "Adjusted",
    }, headers=auth_headers)
    assert update_resp.status_code == 200
    assert update_resp.json()["entry_date"] == "2025-03-11"
    assert update_resp.json()["calories"] == 2050
    assert update_resp.json()["note"] == "Adjusted"


def test_delete_calorie_entry(client, auth_headers):
    create_resp = client.post("/calories/", json={"entry_date": "2025-03-10", "calories": 1900}, headers=auth_headers)
    entry_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/calories/{entry_id}", headers=auth_headers)
    assert delete_resp.status_code == 200

    get_resp = client.get(f"/calories/{entry_id}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_weekly_summary_totals_current_week(client, auth_headers):
    monday = date.today() - timedelta(days=date.today().weekday())
    wednesday = monday + timedelta(days=2)

    client.post("/calories/", json={"entry_date": monday.isoformat(), "calories": 2000}, headers=auth_headers)
    client.post("/calories/", json={"entry_date": wednesday.isoformat(), "calories": 1800}, headers=auth_headers)

    response = client.get("/calories/weekly", headers=auth_headers)
    assert response.status_code == 200
    summary = response.json()
    assert summary["week_start"] == monday.isoformat()
    assert summary["week_end"] == (monday + timedelta(days=6)).isoformat()
    assert summary["total_calories"] == 3800
    assert summary["days_logged"] == 2
    assert summary["average_daily"] == 1900.0
    assert len(summary["entries"]) == 2


def test_weekly_summary_excludes_other_weeks(client, auth_headers):
    monday = date.today() - timedelta(days=date.today().weekday())
    next_monday = monday + timedelta(days=7)

    client.post("/calories/", json={"entry_date": monday.isoformat(), "calories": 2000}, headers=auth_headers)
    client.post("/calories/", json={"entry_date": next_monday.isoformat(), "calories": 2200}, headers=auth_headers)

    response = client.get("/calories/weekly", headers=auth_headers)
    summary = response.json()
    assert summary["total_calories"] == 2000
    assert summary["days_logged"] == 1


def test_weekly_summary_empty_week(client, auth_headers):
    response = client.get("/calories/weekly", headers=auth_headers)
    assert response.status_code == 200
    summary = response.json()
    assert summary["total_calories"] == 0
    assert summary["days_logged"] == 0
    assert summary["average_daily"] == 0.0
    assert summary["entries"] == []


def test_weekly_history_returns_requested_number_of_weeks(client, auth_headers):
    response = client.get("/calories/weekly/history?weeks=4", headers=auth_headers)
    assert response.status_code == 200
    history = response.json()
    assert len(history) == 4
    # Most recent week first
    assert history[0]["week_start"] > history[1]["week_start"]


def test_calorie_entries_scoped_to_owner(client, auth_headers, db):
    """A second user's entries never appear in the first user's list or summary."""
    from app.main import hash_password
    from app import models

    other = models.User(email="other@zest.local", name="Other Chef", password_hash=hash_password("test1234"))
    db.add(other)
    db.commit()
    db.refresh(other)

    login = client.post("/auth/login", json={"email": "other@zest.local", "password": "test1234"})
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    client.post("/calories/", json={"entry_date": "2025-05-05", "calories": 9999}, headers=other_headers)
    client.post("/calories/", json={"entry_date": "2025-05-05", "calories": 1500}, headers=auth_headers)

    response = client.get("/calories/", headers=auth_headers)
    calories = [e["calories"] for e in response.json()]
    assert 9999 not in calories
