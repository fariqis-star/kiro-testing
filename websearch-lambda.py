"""
AWS Lambda - Web Scraper tool for Bedrock Agent Game.

Tries Googlebot UA first (gets server-rendered HTML from SPAs).
Falls back to Chrome UA. Extracts script + body content.
Timeout 25s. Truncates to 25,000 chars.
"""

import json
import re
import ssl
import gzip
import zlib
import io
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

MAX_CONTENT_LENGTH = 25_000
REQUEST_TIMEOUT = 25

NEWLINE = chr(10)
DOUBLE_NEWLINE = chr(10) + chr(10)
BLANK_LINE_PATTERN = chr(10) + r'\s*' + chr(10)

GOOGLEBOT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

CHROME_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Charset": "utf-8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

def _extract_url_from_bedrock_action_group(event):
    parameters = event.get("parameters")
    if isinstance(parameters, list):
        for param in parameters:
            if isinstance(param, dict) and param.get("name") == "url":
                return param.get("value")
    request_body = event.get("requestBody")
    if isinstance(request_body, dict):
        content = request_body.get("content", {})
        json_props = content.get("application/json", {}).get("properties", [])
        if isinstance(json_props, list):
            for prop in json_props:
                if isinstance(prop, dict) and prop.get("name") == "url":
                    return prop.get("value")
    return None

def _extract_url_from_api_gateway(event):
    body = event.get("body")
    if isinstance(body, str):
        try:
            body_json = json.loads(body)
            if isinstance(body_json, dict):
                return body_json.get("url")
        except (json.JSONDecodeError, TypeError):
            pass
    elif isinstance(body, dict):
        return body.get("url")
    return None

def _extract_url(event):
    url = _extract_url_from_bedrock_action_group(event)
    if url:
        return url
    url = event.get("url")
    if url:
        return url
    url = _extract_url_from_api_gateway(event)
    if url:
        return url
    qsp = event.get("queryStringParameters")
    if isinstance(qsp, dict):
        url = qsp.get("url")
        if url:
            return url
    return None

def _fetch_with_headers(url, headers):
    ctx = ssl._create_unverified_context()
    req = Request(url)
    for k, v in headers.items():
        req.add_header(k, v)
    response = urlopen(req, timeout=REQUEST_TIMEOUT, context=ctx)
    raw_data = response.read()

    encoding = response.headers.get("Content-Encoding", "").lower().strip()
    if encoding == "gzip":
        try:
            raw_data = gzip.GzipFile(fileobj=io.BytesIO(raw_data)).read()
        except (OSError, EOFError):
            raw_data = zlib.decompress(raw_data, zlib.MAX_WBITS | 16)
    elif encoding == "deflate":
        try:
            raw_data = zlib.decompress(raw_data)
        except zlib.error:
            raw_data = zlib.decompress(raw_data, -zlib.MAX_WBITS)

    charset = "utf-8"
    content_type = response.headers.get("Content-Type", "")
    ct_match = re.search(r"charset=([\w\-]+)", content_type, re.IGNORECASE)
    if ct_match:
        charset = ct_match.group(1)

    try:
        html = raw_data.decode(charset, errors="replace")
    except (LookupError, UnicodeDecodeError):
        html = raw_data.decode("utf-8", errors="replace")
    return html

def _fetch_page(url):
    """Try Googlebot first (gets SSR content), then Chrome UA."""
    html = ""

    # Try 1: Googlebot UA (servers often return full rendered HTML)
    try:
        html = _fetch_with_headers(url, GOOGLEBOT_HEADERS)
        # Check if we got meaningful content (not just a shell)
        if len(html) > 5000:
            return html
    except Exception:
        pass

    # Try 2: Chrome UA with Referer
    try:
        headers = dict(CHROME_HEADERS)
        headers["Referer"] = "https://www.google.com/"
        headers["DNT"] = "1"
        html = _fetch_with_headers(url, headers)
        if len(html) > 1000:
            return html
    except Exception as e:
        if not html:
            raise e

    # Try 3: Chrome UA without Accept-Encoding
    try:
        headers = dict(CHROME_HEADERS)
        del headers["Accept-Encoding"]
        headers["Referer"] = "https://www.google.com/"
        html = _fetch_with_headers(url, headers)
    except Exception:
        pass

    return html

class _SPATextExtractor(HTMLParser):

    def __init__(self):
        super().__init__()
        self.script_texts = []
        self.body_texts = []
        self._in_script = False
        self._in_style = False
        self._current_script_buffer = []

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower == "script":
            self._in_script = True
            self._current_script_buffer = []
        elif tag_lower == "style":
            self._in_style = True

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower == "script":
            self._in_script = False
            script_content = "".join(self._current_script_buffer).strip()
            if script_content:
                self.script_texts.append(script_content)
            self._current_script_buffer = []
        elif tag_lower == "style":
            self._in_style = False

    def handle_data(self, data):
        if self._in_style:
            return
        if self._in_script:
            self._current_script_buffer.append(data)
        else:
            stripped = data.strip()
            if stripped:
                self.body_texts.append(stripped)

    def handle_entityref(self, name):
        entity_map = {
            "amp": "&", "lt": "<", "gt": ">",
            "quot": '"', "apos": "'", "nbsp": " ",
        }
        char = entity_map.get(name, "&" + name + ";")
        if self._in_script:
            self._current_script_buffer.append(char)
        elif not self._in_style:
            self.body_texts.append(char)

    def handle_charref(self, name):
        try:
            if name.startswith(("x", "X")):
                char = chr(int(name[1:], 16))
            else:
                char = chr(int(name))
        except (ValueError, OverflowError):
            char = "&#" + name + ";"
        if self._in_script:
            self._current_script_buffer.append(char)
        elif not self._in_style:
            self.body_texts.append(char)

def _extract_text(html):
    parser = _SPATextExtractor()
    try:
        parser.feed(html)
    except Exception:
        return _extract_text_regex_fallback(html)

    meaningful_scripts = []
    for script in parser.script_texts:
        if len(script) >= 50 or "{" in script:
            meaningful_scripts.append(script)

    script_output = NEWLINE.join(meaningful_scripts)
    script_output = _fix_unicode_escapes(script_output)
    body_output = " ".join(parser.body_texts)

    # Prioritize body text if it has substantial content
    combined_parts = []
    if body_output.strip() and len(body_output) > 200:
        combined_parts.append(
            "[BODY_TEXT_START]" + NEWLINE + body_output + NEWLINE + "[BODY_TEXT_END]"
        )
    if script_output.strip():
        combined_parts.append(
            "[SCRIPT_CONTENT_START]" + NEWLINE + script_output + NEWLINE + "[SCRIPT_CONTENT_END]"
        )
    if not combined_parts and body_output.strip():
        combined_parts.append(
            "[BODY_TEXT_START]" + NEWLINE + body_output + NEWLINE + "[BODY_TEXT_END]"
        )

    combined = DOUBLE_NEWLINE.join(combined_parts)
    combined = re.sub(r'[ \t]+', ' ', combined)
    combined = re.sub(BLANK_LINE_PATTERN, NEWLINE, combined)
    combined = combined.strip()
    return combined

def _extract_text_regex_fallback(html):
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace("&" + "amp;", "&")
    text = text.replace("&" + "lt;", "<")
    text = text.replace("&" + "gt;", ">")
    text = text.replace("&" + "quot;", '"')
    text = text.replace("&" + "#39;", "'")
    text = text.replace("&" + "nbsp;", " ")
    text = _fix_unicode_escapes(text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(BLANK_LINE_PATTERN, NEWLINE, text)
    text = text.strip()
    return text

def _fix_unicode_escapes(text):
    def _replace_escape(match):
        try:
            return chr(int(match.group(1), 16))
        except (ValueError, OverflowError):
            return match.group(0)
    text = re.sub(r'\\u([0-9a-fA-F]{4})', _replace_escape, text)

    def _replace_hex(match):
        try:
            return chr(int(match.group(1), 16))
        except (ValueError, OverflowError):
            return match.group(0)
    text = re.sub(r'\\x([0-9a-fA-F]{2})', _replace_hex, text)
    return text

def lambda_handler(event, context):
    content = ""
    error = ""

    try:
        url = _extract_url(event)
        if not url:
            error = "No 'url' parameter found in event payload."
        else:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            url = url.strip()
            if url.startswith("http://"):
                url = "https://" + url[7:]

            html = ""
            fetch_error = None

            try:
                html = _fetch_page(url)
            except Exception as e:
                fetch_error = e
                alt_url = url.rstrip("/") + "/" if not url.endswith("/") else url.rstrip("/")
                try:
                    html = _fetch_page(alt_url)
                    fetch_error = None
                except Exception:
                    if "://www." not in url:
                        www_url = url.replace("://", "://www.")
                        try:
                            html = _fetch_page(www_url)
                            fetch_error = None
                        except Exception:
                            pass

            if fetch_error and not html:
                raise fetch_error

            clean_text = _extract_text(html)

            if len(clean_text) > MAX_CONTENT_LENGTH:
                clean_text = clean_text[:MAX_CONTENT_LENGTH]

            content = clean_text

    except HTTPError as exc:
        error = "HTTP error " + str(exc.code) + ": " + str(exc.reason)
    except URLError as exc:
        error = "URL error: " + str(exc.reason)
    except TimeoutError:
        error = "Request timed out."
    except Exception as exc:
        error = "Unexpected error: " + type(exc).__name__ + ": " + str(exc)

    response_body = {
        "content": content,
        "error": error,
    }

    return {
        "statusCode": 200,
        "body": json.dumps(response_body),
    }
