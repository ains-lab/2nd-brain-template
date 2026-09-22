"""Bounded incremental snapshot lab; no checkpoint, scheduler or .env loading.

Demo records are synthetic. posts/matches retain the first capture for legacy
exports. post_versions is content-addressed; observations retain run/query/time
and metrics (the first hit per run/query/version wins on duplicate pages).
database() performs the additive, idempotent migration, including on report().
Legacy observations without verifiable payload provenance cannot be recovered.
Page savepoints protect SQLite consistency, not crash-atomic DB/file commits.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import uuid


class CollectionError(ValueError):
    """Only a controlled reason code may cross the collection/log boundary."""
    def __init__(self, reason):
        import re
        allowed = {'missing_credential', 'missing_user_agent', 'transport_error'}
        self.reason = reason if reason in allowed or re.fullmatch(r'http_[1-5][0-9]{2}', reason) else 'query_failed'
        super().__init__('request_failed')


def utc(value=None):
    if value is None:
        value = dt.datetime.now(dt.timezone.utc)
    elif isinstance(value, (float, int)):
        value = dt.datetime.fromtimestamp(value, dt.timezone.utc)
    elif isinstance(value, str):
        import re
        value = re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', value)
        value = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if value.tzinfo is None:
        raise ValueError('timezone required')
    return value.astimezone(dt.timezone.utc).isoformat().replace('+00:00', 'Z')


def save_json(path, value):
    with open(path, 'x', encoding='utf-8') as handle:
        os.chmod(path, 0o600)
        json.dump(value, handle, ensure_ascii=False)


def database(data):
    """Open/migrate a Path directory's database; caller owns the connection.

    Migration and reporting require write access. Conflicting legacy query IDs
    fail closed rather than assigning ambiguous historical observations.
    """
    connection = sqlite3.connect(data / 'pipeline.sqlite3')
    os.chmod(data / 'pipeline.sqlite3', 0o600)
    connection.row_factory = sqlite3.Row
    connection.executescript('''
    CREATE TABLE IF NOT EXISTS posts (
      platform TEXT, id TEXT, created_at TEXT, collected_at TEXT,
      source_url TEXT, text TEXT, metrics_json TEXT, external_urls_json TEXT,
      PRIMARY KEY(platform,id));
    CREATE TABLE IF NOT EXISTS matches (
      query_id TEXT, platform TEXT, id TEXT, query TEXT, payload_path TEXT,
      UNIQUE(query_id,platform,id));
    CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, started_at TEXT, status TEXT);
    CREATE TABLE IF NOT EXISTS health (
      run_id TEXT, query_id TEXT, platform TEXT, status TEXT, fetched INTEGER,
      reason TEXT);
    CREATE TABLE IF NOT EXISTS post_versions (
      version_id TEXT PRIMARY KEY, platform TEXT, id TEXT, content_hash TEXT,
      created_at TEXT, source_url TEXT, text TEXT, external_urls_json TEXT,
      first_collected_at TEXT, UNIQUE(platform,id,content_hash));
    CREATE TABLE IF NOT EXISTS observations (
      observation_id INTEGER PRIMARY KEY, run_id TEXT, query_id TEXT,
      platform TEXT, id TEXT, version_id TEXT, observed_at TEXT,
      metrics_json TEXT, payload_path TEXT,
      UNIQUE(run_id,query_id,platform,id,version_id));
    CREATE TABLE IF NOT EXISTS query_definitions (
      query_id TEXT PRIMARY KEY, platform TEXT, query TEXT);
    CREATE VIEW IF NOT EXISTS observation_facts AS
      SELECT o.*, v.created_at, v.source_url, v.text, v.external_urls_json,
             v.content_hash, q.query
      FROM observations o JOIN post_versions v USING(version_id)
      LEFT JOIN query_definitions q ON q.query_id=o.query_id AND q.platform=o.platform;
    ''')
    try:
        with connection:
            register_queries(connection, connection.execute(
                'SELECT DISTINCT query_id AS id,platform,query FROM matches'))
            # First-capture rows are immutable compatibility records. Migrate only
            # identities not yet represented; never synthesize historical runs.
            for row in connection.execute('''SELECT p.* FROM posts p WHERE NOT EXISTS
                    (SELECT 1 FROM post_versions v WHERE v.platform=p.platform AND v.id=p.id)'''):
                post = dict(row)
                post['external_urls'] = json.loads(post['external_urls_json'])
                version_id = store_version(connection, post['platform'], post, post['collected_at'])
                backfill_observations(connection, data, post, version_id)
    except Exception:
        connection.close()
        raise
    return connection


def register_queries(connection, queries):
    """Lock each query ID to its original meaning, including zero-hit queries."""
    for query in queries:
        original = connection.execute('SELECT platform,query FROM query_definitions WHERE query_id=?',
                                      (query['id'],)).fetchone()
        if original is not None and tuple(original) != (query['platform'], query['query']):
            raise ValueError('query_id conflict')
        connection.execute('INSERT OR IGNORE INTO query_definitions VALUES (?,?,?)',
                           (query['id'], query['platform'], query['query']))


def content_hash(platform, post):
    """Return the SHA-256 identity of canonical UTF-8 content, not metrics.

    URL list order is significant. Dates are normalized to UTC; no text or URL
    normalization is done here. Only the six documented content fields are used.
    """
    content = {key: post[key] for key in ('id', 'source_url', 'text', 'external_urls')}
    content.update(platform=platform, created_at=utc(post['created_at']))
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def store_version(connection, platform, post, collected_at):
    """Insert an immutable version if absent; return its content-derived ID."""
    digest = content_hash(platform, post)
    connection.execute('INSERT OR IGNORE INTO post_versions VALUES (?,?,?,?,?,?,?,?,?)',
                       (digest, platform, post['id'], digest, utc(post['created_at']),
                        post['source_url'], post['text'], json.dumps(post['external_urls']), collected_at))
    return digest


def backfill_observations(connection, data, post, version_id):
    """Recover only an original version's evidenced legacy matches.

    Missing/invalid/out-of-directory payloads, unknown runs and changed content
    cannot establish provenance: keep the version, omit the observation. Legacy
    dedup discarded repeat observations; those cannot be reconstructed. This is
    attempted only when a legacy post has no version, not on every database open.
    """
    for match in connection.execute('SELECT * FROM matches WHERE platform=? AND id=?',
                                    (post['platform'], post['id'])):
        try:
            path = Path(match['payload_path'])
            if (path.is_symlink() or path.resolve().parent != data.resolve() or
                    path.suffix != '.json' or path.stat().st_size > 5_000_000):
                continue
            envelope = json.loads(path.read_text(encoding='utf-8'))
            if any(envelope[key] != match[key] for key in ('query_id', 'platform', 'query')):
                continue
            if not connection.execute('SELECT 1 FROM runs WHERE id=?', (envelope['run_id'],)).fetchone():
                continue
            if not isinstance(envelope['collected_at'], str):
                continue
            observed_at = utc(envelope['collected_at'])
            for item in envelope['posts']:
                if item['id'] != post['id'] or content_hash(post['platform'], item) != version_id:
                    continue
                if not isinstance(item['metrics'], dict):
                    continue
                metrics_json = json.dumps(item['metrics'], allow_nan=False)
                connection.execute('''INSERT OR IGNORE INTO observations
                    (run_id,query_id,platform,id,version_id,observed_at,metrics_json,payload_path)
                    VALUES (?,?,?,?,?,?,?,?)''',
                                   (envelope['run_id'], match['query_id'], post['platform'], post['id'],
                                    version_id, observed_at, metrics_json, match['payload_path']))
        except (OSError, ValueError, KeyError, TypeError):
            # Do not echo legacy payloads or paths into health/error output.
            continue


def demo_page(platform, query, token):
    return {'posts': [{'id': 'synthetic-1', 'created_at': '2026-01-01T00:00:00Z',
                      'source_url': 'https://example.invalid/' + platform + '/synthetic-1',
                      'text': '[SYNTHETIC DEMO] Hermes OMH keyword search',
                      'metrics': {}, 'external_urls': []}], 'next_token': None}


def safe_token(token):
    import re
    if token is not None and (not isinstance(token, str) or
                              not re.fullmatch(r'[A-Za-z0-9_.=~+/-]{1,2048}', token) or
                              token.startswith('//')):
        raise ValueError('unsafe pagination token')
    return token


def safe_url(value):
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
    parts = urlsplit(value or '')
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username:
        return ''
    # Preserve article identity such as ?id=42; drop known credential fields.
    secret_keys = {'access_token', 'token', 'api_key', 'apikey', 'key',
                   'authorization', 'signature', 'sig', 'client_secret'}
    query = [(key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
             if key.lower() not in secret_keys]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ''))


class Live:
    def __init__(self, env=None, transport=None):
        self.env = os.environ if env is None else env
        self.transport = transport or http_get

    def __call__(self, platform, query, token):
        safe_token(token)
        names = {'x': 'X_BEARER_TOKEN', 'threads': 'THREADS_ACCESS_TOKEN',
                 'reddit': 'REDDIT_ACCESS_TOKEN'}
        bearer = self.env.get(names[platform])
        if not bearer:
            raise CollectionError('missing_credential')
        headers = {'Authorization': 'Bearer ' + bearer}
        if platform == 'x':
            url = 'https://api.x.com/2/tweets/search/recent'
            params = {'query': query, 'max_results': 100,
                      'tweet.fields': 'created_at,lang,public_metrics,entities'}
            cursor = 'next_token'
        elif platform == 'threads':
            url = 'https://graph.threads.net/keyword_search'
            params = {'q': query, 'search_type': 'RECENT',
                      'fields': 'id,text,timestamp,permalink'}
            cursor = 'after'
        else:
            url = 'https://oauth.reddit.com/search'
            params = {'q': query, 'sort': 'new', 'type': 'link', 'limit': 100, 'raw_json': 1}
            cursor = 'after'
            headers['User-Agent'] = self.env.get('REDDIT_USER_AGENT', '')
            if not headers['User-Agent']:
                raise CollectionError('missing_user_agent')
        if token:
            params[cursor] = token
        raw = self.transport(url, params, headers)
        # Capture an allowlisted response projection, never paging.next or headers.
        # This is deliberately NOT a byte-exact raw API archive.
        if raw.get('errors') or raw.get('error'):
            raise ValueError('API response error')
        if platform == 'reddit':
            records = [child['data'] for child in raw['data']['children']]
            next_token = raw['data'].get('after')
        else:
            records = raw.get('data', [])
            if platform == 'x':
                next_token = raw.get('meta', {}).get('next_token')
            else:
                paging = raw.get('paging', {})
                next_token = paging.get('cursors', {}).get('after') if paging.get('next') else None
                if paging.get('next') and not next_token:
                    raise ValueError('missing pagination cursor')
        posts = []
        for item in records:
            identifier = str(item['id'])
            if platform == 'x':
                created = item['created_at']
                text = item.get('text', '')
                source = 'https://x.com/i/web/status/' + identifier
                metrics = item.get('public_metrics', {})
                urls = [u.get('expanded_url', '') for u in item.get('entities', {}).get('urls', [])]
            elif platform == 'threads':
                created, text = item['timestamp'], item.get('text', '')
                source, metrics, urls = item.get('permalink', ''), {}, []
            else:
                created = item['created_utc']
                text = item.get('title', '') + '\n' + item.get('selftext', '')
                source = 'https://www.reddit.com' + item['permalink']
                metrics = {k: item[k] for k in ('score', 'num_comments', 'upvote_ratio') if k in item}
                urls = [item.get('url', '')]
            post = {'id': identifier, 'created_at': utc(created), 'text': text,
                    'source_url': safe_url(source), 'metrics': metrics,
                    'external_urls': [safe_url(u) for u in urls if safe_url(u)]}
            # Redact any accidentally echoed supplied bearer value, including text.
            encoded = json.dumps(post, ensure_ascii=False)
            encoded = encoded.replace(bearer, '[REDACTED]')
            posts.append(json.loads(encoded))
        return {'posts': posts, 'next_token': safe_token(next_token)}


def http_get(url, params, headers, opener=None, sleep=None):
    import time
    from urllib.parse import urlencode
    from urllib.request import Request, build_opener, HTTPRedirectHandler
    from urllib.error import HTTPError

    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hdrs, newurl):
            return None

    opener = opener or build_opener(NoRedirect()).open
    sleep = sleep or time.sleep
    request = Request(url + '?' + urlencode(params), headers=headers, method='GET')
    for attempt in range(3):
        try:
            with opener(request, timeout=20) as response:
                body = response.read(5_000_001)
                if len(body) > 5_000_000:
                    raise ValueError('response too large')
                return json.loads(body)
        except HTTPError as error:
            retry = error.code == 429 or 500 <= error.code <= 599
            # Do not read or print the response body/URL. Honor short Retry-After;
            # abort rather than retry too early when the server asks for >30s.
            retry_after = error.headers.get('Retry-After') if error.headers else None
            if error.fp is not None:
                error.fp.close()
            delay = 2 ** attempt
            if retry_after:
                try:
                    delay = max(delay, float(retry_after))
                except ValueError:
                    retry = False
            if not retry or attempt == 2 or not 0 <= delay <= 30:
                raise CollectionError('http_' + str(error.code)) from None
            sleep(delay)
        except Exception:
            raise CollectionError('transport_error') from None
    raise ValueError('request_failed')


def validate(config):
    if not isinstance(config, dict) or not isinstance(config.get('queries'), list):
        raise ValueError('invalid config')
    pages = config.get('max_pages', 2)
    if type(pages) is not int or not 1 <= pages <= 10:
        raise ValueError('max_pages must be 1..10')
    ids = set()
    for query in config['queries']:
        if (not isinstance(query, dict) or
                query.get('platform') not in ('x', 'threads', 'reddit') or
                type(query.get('enabled', True)) is not bool or
                any(not isinstance(query.get(k), str) or not query[k].strip() for k in ('id', 'query')) or
                query['id'] in ids):
            raise ValueError('invalid query')
        ids.add(query['id'])


def validate_page(page):
    """Reject malformed normalized records before persisting any part of a page."""
    if not isinstance(page, dict) or not isinstance(page.get('posts'), list):
        raise ValueError('invalid page')
    safe_token(page['next_token'])
    for post in page['posts']:
        if (not isinstance(post, dict) or
                any(not isinstance(post.get(key), str) for key in ('id', 'source_url', 'text')) or
                not post['id'] or post.get('created_at') is None or
                not isinstance(post.get('metrics'), dict) or
                not isinstance(post.get('external_urls'), list) or
                any(not isinstance(url, str) for url in post['external_urls'])):
            raise ValueError('invalid post')
        utc(post['created_at'])
    # Serialize before save_json creates a file, including unknown adapter fields.
    json.dumps(page['posts'], allow_nan=False)


def run(config, data_dir, mode, fetch=None):
    validate(config)
    fetch = fetch or (demo_page if mode == 'demo' else Live())
    data = Path(data_dir).expanduser().absolute()
    if mode not in ('demo', 'live'):
        raise ValueError('invalid mode')
    marker = data / 'mode.json'
    if data.is_symlink():
        raise ValueError('symlink data directory refused')
    if data.exists() and not marker.exists() and any(data.iterdir()):
        raise ValueError('use a new empty data directory')
    if marker.exists() and json.loads(marker.read_text()) != {'mode': mode}:
        raise ValueError('demo/live directory mismatch')
    data.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(data, 0o700)
    if not marker.exists():
        save_json(marker, {'mode': mode})
    connection = database(data)
    try:
        with connection:
            register_queries(connection, config['queries'])
    except Exception:
        connection.close()
        raise
    run_id = uuid.uuid4().hex
    connection.execute('INSERT INTO runs VALUES (?,?,?)', (run_id, utc(), 'ok'))
    overall = 'ok'
    for query in config['queries']:
        if not query.get('enabled', True):
            continue
        status, reason, fetched, token = 'ok', '', 0, None
        try:
            for _ in range(config.get('max_pages', 2)):
                page = (fetch or demo_page)(query['platform'], query['query'], token)
                payload = data / (uuid.uuid4().hex + '.json')
                collected = utc()
                connection.execute('SAVEPOINT collection_page')
                try:
                    validate_page(page)
                    for post in page['posts']:
                        connection.execute('INSERT OR IGNORE INTO posts VALUES (?,?,?,?,?,?,?,?)',
                                           (query['platform'], post['id'], utc(post['created_at']), collected,
                                            post['source_url'], post['text'], json.dumps(post['metrics']),
                                            json.dumps(post['external_urls'])))
                        connection.execute('INSERT OR IGNORE INTO matches VALUES (?,?,?,?,?)',
                                           (query['id'], query['platform'], post['id'], query['query'], str(payload)))
                        version_id = store_version(connection, query['platform'], post, collected)
                        connection.execute('''INSERT OR IGNORE INTO observations
                            (run_id,query_id,platform,id,version_id,observed_at,metrics_json,payload_path)
                            VALUES (?,?,?,?,?,?,?,?)''',
                                           (run_id, query['id'], query['platform'], post['id'], version_id,
                                            collected, json.dumps(post['metrics']), str(payload)))
                    next_token = page['next_token']
                    save_json(payload, {'run_id': run_id, 'mode': mode,
                                        'platform': query['platform'], 'query_id': query['id'],
                                        'query': query['query'], 'collected_at': collected,
                                        'posts': page['posts'], 'has_more': bool(next_token)})
                except Exception:
                    connection.execute('ROLLBACK TO collection_page')
                    connection.execute('RELEASE collection_page')
                    raise
                connection.execute('RELEASE collection_page')
                fetched += len(page['posts'])
                token = next_token
                if not token:
                    break
            if token:
                status, reason = 'partial', 'page_cap'
        except Exception as error:
            status = 'partial' if fetched else 'error'
            reason = error.reason if isinstance(error, CollectionError) else 'query_failed'
        if status != 'ok':
            overall = 'error' if status == 'error' or overall == 'error' else 'partial'
        connection.execute('INSERT INTO health VALUES (?,?,?,?,?,?)',
                           (run_id, query['id'], query['platform'], status, fetched, reason))
    connection.execute('UPDATE runs SET status=? WHERE id=?', (overall, run_id))
    connection.commit()
    connection.close()
    return int(overall != 'ok')


def report(data_dir):
    """Migrate if needed, count versions/observations, and export legacy rows."""
    data = Path(data_dir).expanduser().absolute()
    mode = json.loads((data / 'mode.json').read_text())['mode']
    connection = database(data)
    result = {table: connection.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
              for table in ('posts', 'matches', 'runs', 'observations')}
    result['versions'] = connection.execute('SELECT COUNT(*) FROM post_versions').fetchone()[0]
    result['failed_runs'] = connection.execute("SELECT COUNT(*) FROM runs WHERE status != 'ok'").fetchone()[0]
    result['health'] = [dict(row) for row in connection.execute('SELECT * FROM health')]
    export = data / ('export-' + uuid.uuid4().hex + '.jsonl')
    with open(export, 'x', encoding='utf-8') as handle:
        os.chmod(export, 0o600)
        for row in connection.execute('SELECT * FROM posts JOIN matches USING(platform,id)'):
            item = dict(row)
            item['mode'] = mode
            item['metrics'] = json.loads(item.pop('metrics_json'))
            item['external_urls'] = json.loads(item.pop('external_urls_json'))
            handle.write(json.dumps(item, ensure_ascii=False) + '\n')
    result['export'] = str(export)
    connection.close()
    return result


def main():
    import argparse
    import sys
    parser = argparse.ArgumentParser(description='SNS 키워드 스냅샷 실습 (데모/실제 데이터 분리)')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--data-dir', type=Path,
                        default=Path.home() / '.local/share/hermes-sns-lab')
    parser.add_argument('--mode', choices=('demo', 'live'), default='demo')
    parser.add_argument('--report', action='store_true')
    args = parser.parse_args()
    try:
        if args.report:
            print(json.dumps(report(args.data_dir), ensure_ascii=False, indent=2))
            return 0
        if args.config is None:
            parser.error('--config is required unless --report is used')
        config = json.loads(args.config.read_text(encoding='utf-8'))
        code = run(config, args.data_dir, args.mode)
        print(json.dumps({'mode': args.mode, 'status': 'ok' if code == 0 else 'partial_or_error'}))
        return code
    except Exception:
        print('실행 실패: 설정·전용 데이터 폴더·모드·권한을 확인하세요. 비밀값/응답 본문은 출력하지 않습니다.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
