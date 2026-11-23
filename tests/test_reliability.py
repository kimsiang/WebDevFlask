"""Startup, failures, and public input boundaries."""

import pytest
import pymysql

from conftest import Result


def test_factory_and_home_do_not_connect_to_database(database_stub):
    from app import create_app

    application = create_app({"TESTING": True, "DB_USER": "", "DB_NAME": ""})
    assert application.test_client().get("/").status_code == 200
    assert database_stub.connect_calls == []
    assert not application.debug


def test_missing_configuration_has_controlled_503(database_stub):
    from app import create_app

    application = create_app({"TESTING": True, "DB_USER": "", "DB_NAME": ""})
    response = application.test_client().get("/sipm")
    assert response.status_code == 503
    assert database_stub.connect_calls == []
    assert "database" in response.get_data(as_text=True).lower()
    assert "Traceback" not in response.get_data(as_text=True)


def test_connection_failure_does_not_expose_internal_details(app, database_stub):
    database_stub.connect_error = pymysql.OperationalError(2003, "secret-host private-password")
    response = app.test_client().get("/sipm")
    assert response.status_code == 503
    assert b"secret-host" not in response.data
    assert b"private-password" not in response.data
    assert b"Traceback" not in response.data


def test_query_failure_closes_resources_and_can_recover(app, database_stub):
    database_stub.queue(Result(error=pymysql.OperationalError(2013, "secret connection detail")))
    database_stub.queue(Result(rows=((2, "recovered"),)))
    client = app.test_client()
    failure = client.get("/sipm")
    assert failure.status_code == 503
    assert b"secret connection detail" not in failure.data
    failed_connection = database_stub.connections[0]
    assert failed_connection.closed
    assert all(cursor.closed for cursor in failed_connection.cursors)
    success = client.get("/sipm")
    assert success.status_code == 200
    assert b"recovered" in success.data
    assert database_stub.connections[1].closed


@pytest.mark.parametrize("identifier", ["0", "25", "-1", "not-a-number", "1%20OR%201=1", "1%3BSELECT%201"])
def test_invalid_calorimeter_identifier_never_reaches_sql(app, database_stub, identifier):
    response = app.test_client().get(f"/calo_vis/{identifier}")
    assert response.status_code == 404
    assert database_stub.connect_calls == []


def test_calorimeter_identifier_is_a_bound_parameter(app, database_stub):
    database_stub.queue(Result())
    response = app.test_client().get("/calo_vis/7")
    assert response.status_code == 200
    sql, parameters = database_stub.connections[0].queries[0]
    assert "%s" in sql
    assert parameters[-1] == 7
    assert sql.count("%s") == len(parameters)
    assert "calo_id = %s" in sql


@pytest.mark.parametrize("payload", [{}, {"inputName": "a", "inputEmail": "a@example.com", "inputPassword": "unused"}])
def test_historical_signup_cannot_claim_to_create_accounts(app, database_stub, payload):
    response = app.test_client().post("/signUp", data=payload)
    assert response.status_code == 410
    assert b"All fields good" not in response.data
    assert database_stub.connect_calls == []


def test_static_php_writer_is_not_exposed(app):
    assert app.test_client().get("/static/js/field_update.php").status_code == 404


def test_retired_signup_page_does_not_collect_credentials(app, database_stub):
    response = app.test_client().get("/showSignUp")
    assert response.status_code == 410
    assert b'type="password"' not in response.data
    assert database_stub.connect_calls == []


def test_missing_tls_ca_file_returns_safe_503(app, database_stub):
    private_path = "/private/experiment/tls-ca.pem"
    app.config["DB_SSL_CA"] = private_path
    database_stub.connect_error = FileNotFoundError(2, "No such file", private_path)
    response = app.test_client().get("/sipm")
    assert response.status_code == 503
    assert private_path not in response.get_data(as_text=True)
    assert b"Traceback" not in response.data
    assert database_stub.connect_calls[0]["ssl_verify_cert"] is True
    assert database_stub.connect_calls[0]["ssl_verify_identity"] is True
    assert database_stub.connections == []
