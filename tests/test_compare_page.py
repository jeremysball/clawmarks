from clawmarks.build import compare_page


def test_render_html_includes_compare_api_calls():
    html = compare_page.render_html()
    assert "/api/compare/next" in html
    assert "/api/compare" in html


def test_render_html_has_two_panes():
    html = compare_page.render_html()
    assert 'id="pane1"' in html
    assert 'id="pane2"' in html
    assert 'id="img1"' in html
    assert 'id="img2"' in html


def test_render_html_has_no_button_elements():
    html = compare_page.render_html()
    assert "<button" not in html


def test_render_html_has_zoom_icons_and_overlay():
    html = compare_page.render_html()
    assert 'id="zoom1"' in html
    assert 'id="zoom2"' in html
    assert 'id="zoom-overlay"' in html
    assert "function openZoom(" in html
    assert "function closeZoom(" in html


def test_render_html_has_arrow_key_handling():
    html = compare_page.render_html()
    assert "ArrowLeft" in html
    assert "ArrowRight" in html


def test_render_html_has_session_count():
    html = compare_page.render_html()
    assert 'id="count"' in html
    assert "comparedThisSession" in html


def test_render_html_has_done_state():
    html = compare_page.render_html()
    assert 'id="done"' in html
