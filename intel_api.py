"""HTTP endpoints for the local analysis workspace."""
import threading
from flask import Blueprint, request, jsonify, send_from_directory
import intel
import skanning as sk

bp = Blueprint('intel', __name__)
_lock = threading.Lock()
_job = {'running': False, 'result': None, 'error': None}

@bp.route('/analys')
def page():
    return send_from_directory(sk.HAR, 'analys.html')

@bp.route('/analys.js')
def script():
    return send_from_directory(sk.HAR, 'analys.js')

@bp.route('/api/intel')
def overview():
    return jsonify(intel.overview())

@bp.route('/api/intel/<symbol>')
def detail(symbol):
    try:
        return jsonify(intel.detail(symbol))
    except ValueError as exc:
        return jsonify(fel=str(exc)), 404

@bp.route('/api/intel/note', methods=['POST'])
def note():
    try:
        return jsonify(id=intel.add_note(request.get_json() or {}))
    except (ValueError, TypeError) as exc:
        return jsonify(fel=str(exc)), 400

@bp.route('/api/intel/note/<int:note_id>/archive', methods=['POST'])
def archive(note_id):
    with intel.connect() as db:
        cur = db.execute('UPDATE notes SET active=0 WHERE id=?', (note_id,))
    return jsonify(ok=cur.rowcount > 0)

@bp.route('/api/intel/scenario', methods=['POST'])
def scenario():
    try:
        return jsonify(intel.scenario(request.get_json() or {}))
    except (ValueError, TypeError) as exc:
        return jsonify(fel=str(exc)), 400

@bp.route('/api/intel/job')
def job():
    with _lock:
        return jsonify(dict(_job))

@bp.route('/api/intel/refresh', methods=['POST'])
def refresh():
    data = request.get_json() or {}
    symbol = data.get('symbol')
    action = data.get('action', 'refresh')
    if action not in ('refresh', 'evaluate'):
        return jsonify(fel='Okänd åtgärd'), 400
    if action == 'refresh' and (not isinstance(symbol, str) or symbol not in intel.overview()['bolag']):
        return jsonify(fel='Välj ett bolag'), 400
    with _lock:
        if _job['running']:
            return jsonify(fel='Ett analysjobb kör redan'), 409
        _job.update(running=True, result=None, error=None)
    def run():
        try:
            if action == 'evaluate':
                result = intel.evaluate()
            else:
                c = sk.detaljer(symbol)
                if c.get('fel'):
                    raise ValueError(c['fel'])
                intel.snapshot({'tid': intel.now(), 'analysversion': intel.VERSION, 'case': [c]})
                result = {'symbol': symbol, 'status': 'Ny analys sparad'}
            with _lock:
                _job['result'] = result
        except Exception as exc:
            with _lock:
                _job['error'] = str(exc)
        finally:
            with _lock:
                _job['running'] = False
    threading.Thread(target=run, daemon=True).start()
    return jsonify(started=True), 202


@bp.route('/api/intel/snapshot/<int:snapshot_id>')
def historical_snapshot(snapshot_id):
    import json
    with intel.connect() as db:
        row=db.execute('SELECT * FROM snapshots WHERE id=?',(snapshot_id,)).fetchone()
    if not row:
        return jsonify(fel='Analysen finns inte'),404
    return jsonify(id=row['id'],observed=row['observed'],scan_time=row['scan_time'],
                   version=row['version'],data=json.loads(row['payload']))


@bp.route('/api/intel/<symbol>/nyckeltal')
def key_figures(symbol):
    import nyckeltal
    try:
        _, c = intel.latest(symbol)
        return jsonify(nyckeltal.build(c, request.args.get('period','annual')))
    except ValueError as exc:
        return jsonify(fel=str(exc)),400
