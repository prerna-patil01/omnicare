from io import BytesIO
from pathlib import Path

import fitz
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Biomarker, Report, ReportExtraction, ReportPage, User


def upload(client, headers, name, body, content_type):
    return client.post(
        "/api/reports",
        headers=headers,
        data={"file": (BytesIO(body), name, content_type)},
        content_type="multipart/form-data",
    )


def pdf_with_pages(*texts):
    document = fitz.open()
    for text in texts:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    result = document.tobytes()
    document.close()
    return result


def test_text_report_extracts_one_page_and_existing_biomarker(client, auth_headers):
    response = upload(
        client, auth_headers, "results.txt", b"Haemoglobin: 14.2\nNo other result", "text/plain"
    )

    assert response.status_code == 201
    report = response.json["data"]["report"]
    assert report["extraction"]["status"] == "completed"
    assert report["extraction"]["parser"] == "utf-8"
    assert report["extraction"]["pageCount"] == 1
    assert report["biomarkers"][0]["label"] == "Haemoglobin"
    assert report["biomarkers"][0]["source"] == "extracted"


def test_pdf_extraction_preserves_each_page(client, auth_headers):
    response = upload(
        client, auth_headers, "results.pdf", pdf_with_pages("First page", "Second page"), "application/pdf"
    )

    report = response.json["data"]["report"]
    assert response.status_code == 201
    assert report["extraction"]["status"] == "completed"
    assert report["extraction"]["pageCount"] == 2

    details = client.get(f"/api/reports/{report['id']}/extraction", headers=auth_headers)
    assert details.status_code == 200
    pages = details.json["data"]["extraction"]["pages"]
    assert [page["pageNumber"] for page in pages] == [1, 2]
    assert all(page["characterCount"] > 0 for page in pages)


def test_empty_pdf_is_retained_but_has_explicit_extraction_failure(client, app, auth_headers):
    response = upload(client, auth_headers, "scanned.pdf", pdf_with_pages(""), "application/pdf")

    assert response.status_code == 201
    report_id = response.json["data"]["report"]["id"]
    extraction = response.json["data"]["report"]["extraction"]
    assert extraction["status"] == "failed"
    assert "No extractable text" in extraction["error"]
    assert response.json["data"]["report"]["biomarkers"] == []

    with app.app_context():
        report = db.session.get(Report, report_id)
        assert Path(report.stored_path).is_file()
        assert db.session.query(Biomarker).filter_by(report_id=report_id).count() == 0
        assert db.session.query(ReportPage).filter_by(report_id=report_id).count() == 1


def test_invalid_pdf_masquerading_as_pdf_is_rejected(client, auth_headers):
    response = upload(client, auth_headers, "not-a-report.pdf", b"%PDF-not-a-real-pdf", "application/pdf")

    assert response.status_code == 415
    assert "readable PDF" in response.json["message"]


def test_unsupported_and_oversized_reports_are_rejected(client, auth_headers):
    unsupported = upload(client, auth_headers, "results.exe", b"not executable", "application/octet-stream")
    oversized = upload(client, auth_headers, "large.txt", b"a" * (10 * 1024 * 1024 + 1), "text/plain")

    assert unsupported.status_code == 415
    assert oversized.status_code == 413


def test_image_report_requires_ocr_without_creating_biomarkers(client, app, auth_headers):
    png = b"\x89PNG\r\n\x1a\n" + b"not-a-real-image"
    response = upload(client, auth_headers, "scan.png", png, "image/png")

    assert response.status_code == 201
    report_id = response.json["data"]["report"]["id"]
    assert response.json["data"]["report"]["extraction"]["status"] == "needs_ocr"
    with app.app_context():
        assert db.session.query(Biomarker).filter_by(report_id=report_id).count() == 0


def test_extraction_endpoint_requires_owner(client, app, auth_headers):
    report = upload(client, auth_headers, "mine.txt", b"No biomarkers", "text/plain").json["data"]["report"]
    assert client.get(f"/api/reports/{report['id']}/extraction").status_code == 401

    with app.app_context():
        other = User(email="other@example.com", full_name="Other User")
        other.set_password("not-used-in-this-test")
        db.session.add(other)
        db.session.commit()
        other_token = create_access_token(identity=other.id)

    denied = client.get(
        f"/api/reports/{report['id']}/extraction",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert denied.status_code == 404
