import asyncio
import io

CSV_CONTENT = b"""Store ID,SKU,Product Name,Price,Date
ST001,SKU100,Wireless Mouse,19.99,2026-01-05
ST001,SKU101,USB Cable,5.50,2026-01-05
ST002,SKU100,Wireless Mouse,21.99,2026-01-05
"""


async def upload_csv(client, auth_headers, content=CSV_CONTENT, filename="feed.csv"):
    """Posts the feed and polls the job status until the (async) ingestion finishes,
    mirroring how the SPA polls GET /api/uploads/{job_id} after a 202 response."""
    files = {"file": (filename, io.BytesIO(content), "text/csv")}
    resp = await client.post("/api/uploads", files=files, headers=auth_headers)
    if resp.status_code != 202:
        return resp

    job_id = resp.json()["id"]
    for _ in range(50):
        resp = await client.get(f"/api/uploads/{job_id}", headers=auth_headers)
        if resp.json()["status"] in ("COMPLETED", "FAILED"):
            return resp
        await asyncio.sleep(0.02)
    return resp


async def test_upload_requires_api_key(client):
    resp = await upload_csv(client, auth_headers={})
    assert resp.status_code in (401, 422)


async def test_upload_and_search_roundtrip(client, auth_headers):
    resp = await upload_csv(client, auth_headers)
    assert resp.status_code == 200
    job = resp.json()
    assert job["status"] == "COMPLETED"
    assert job["inserted_rows"] == 3
    assert job["error_rows"] == 0

    resp = await client.get("/api/pricing", params={"store_id": "ST001"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert {r["sku"] for r in body["items"]} == {"SKU100", "SKU101"}


async def test_upload_upsert_updates_existing_record(client, auth_headers):
    await upload_csv(client, auth_headers)
    updated_csv = b"""Store ID,SKU,Product Name,Price,Date
ST001,SKU100,Wireless Mouse v2,24.99,2026-01-05
"""
    resp = await upload_csv(client, auth_headers, content=updated_csv)
    job = resp.json()
    assert job["inserted_rows"] == 0
    assert job["updated_rows"] == 1

    resp = await client.get("/api/pricing", params={"store_id": "ST001", "sku": "SKU100"}, headers=auth_headers)
    item = resp.json()["items"][0]
    assert item["product_name"] == "Wireless Mouse v2"
    assert item["price"] == "24.99"


async def test_upload_reports_row_errors(client, auth_headers):
    bad_csv = b"""Store ID,SKU,Product Name,Price,Date
ST001,SKU200,Bad Price Item,not-a-number,2026-01-05
ST001,SKU201,Good Item,9.99,2026-01-05
"""
    resp = await upload_csv(client, auth_headers, content=bad_csv)
    job = resp.json()
    assert job["error_rows"] == 1
    assert job["inserted_rows"] == 1
    assert any("line 2" in e for e in job["errors"])


async def test_search_price_range_and_product_name(client, auth_headers):
    await upload_csv(client, auth_headers)
    resp = await client.get(
        "/api/pricing",
        params={"product_name": "mouse", "min_price": 20, "max_price": 30},
        headers=auth_headers,
    )
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["store_id"] == "ST002"


async def test_edit_record_writes_audit_log(client, auth_headers):
    await upload_csv(client, auth_headers)
    resp = await client.get("/api/pricing", params={"store_id": "ST001", "sku": "SKU100"}, headers=auth_headers)
    record_id = resp.json()["items"][0]["id"]

    resp = await client.patch(
        f"/api/pricing/{record_id}", json={"price": 17.49}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["price"] == "17.49"

    resp = await client.get(f"/api/pricing/{record_id}/history", headers=auth_headers)
    history = resp.json()
    assert len(history) == 1
    assert history[0]["field_name"] == "price"
    assert history[0]["old_value"] == "19.99"
    assert history[0]["new_value"] == "17.49"
    assert history[0]["changed_by"] == "test-user"


async def test_edit_nonexistent_record_returns_404(client, auth_headers):
    resp = await client.patch("/api/pricing/999999", json={"price": 1}, headers=auth_headers)
    assert resp.status_code == 404


async def test_reject_non_csv_upload(client, auth_headers):
    files = {"file": ("feed.txt", io.BytesIO(b"hello"), "text/plain")}
    resp = await client.post("/api/uploads", files=files, headers=auth_headers)
    assert resp.status_code == 400
