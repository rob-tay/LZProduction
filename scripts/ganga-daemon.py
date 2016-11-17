import os
import sys
import argparse
import importlib
import ganga
from contextlib import contextmanager
from daemonize import Daemonize

@contextmanager
def auto_cleanup_request():
    req = ganga.LZRequest()
    try:
        yield req
    except:
        req.remove(remove_jobs=True)
        raise

def getGangaRequest(requestdb_id):
    # note could use tasks.select here
    for t in ganga.tasks:
        if t.requestdb_id == requestdb_id:
            return t
    return None


def monitor_requests(dburl):
    with sqlalchemy_utils.db_session(dburl) as session:
        monitored_requests = session.query(Requests)\
                                    .filter(Requests.status != 'Completed')\
                                    .filter(Request.status != 'New')\
                                    .all()

        approved_requests = ((r, getGangaRequest(r.id)) for r in monitored_requests
                             if r.status == "Approved")
        paused_requests = ((r, getGangaRequest(r.id)) for r in monitored_requests
                           if r.status == "Paused")
        running_requests = ((r, getGangaRequest(r.id)) for r in monitored_requests
                            if r.status == "Running")

        for request, ganga_request in approved_requests:
            if ganga_request is not None
            # why is it still approved?
            session.query(Requests)\
                   .filter(Requests.id == request.id)\
                   .update(status=ganga_request.status.capitalize())
            continue
            t.requestdb_id = request.id
            t.requestdb_status = request.status
            tr = ganga.CoreTransform(backend=ganga.Dirac())
            tr.application = ganga.LZApp()
            tr.application.luxsim_version=request.app_version
            tr.application.reduction_version = request.reduction_version
            tr.application.requestid = request.id
            tr.application.tag = request.tag
            macros, njobs, nevents, seed = zip(*(i.split() for i in request.selected_macros.splitlines()))
            tr.unit_splitter = GenericSplitter()
            tr.unit_splitter.multi_attrs={'application.macro': macros,
                                          'application.njobs': [int(i) for i in njobs],
                                          'application.nevents': [int(i) for i in nevents],
                                          'application.seed': [int(i) for i in seed]}
            t.appendTransform(tr)
            t.float = 100
            t.run()
            session.query(Requests)\
                   .filter(Requests.id == request.id)\
                   .update(status=t.status.capitalize())

        for request, ganga_request in paused_requests:
            if ganga_request is not None and ganga_request.status != "paused":
                session.query(Requests)\
                       .filter(Requests.id == request.id)\
                       .update(status=ganga_request.status.capitalize())

        for request, ganga_request in running_requests:
            if ganga_request.status not in ['paused', 'completed']:
                raise Exception("This should not happen")

            if ganga_request.status == "completed":
                # job completed, time to feed stuff back
                pass

            session.query(Requests)\
                   .filter(Requests.id == request.id)\
                   .update(status=ganga_request.status.capitalize())


                with session.begin_nested():
                    with auto_cleanup_request() as t:


if __name__ == '__main__':
    lzprod_root = os.path.dirname(os.path.dirname(os.path.expanduser(os.path.expandvars(os.path.realpath(os.path.abspath(__file__))))))

    parser = argparse.ArgumentParser(description='Run the ganga job submission daemon.')
    parser.add_argument('-d', '--dburl', default="sqlite:///" + os.path.join(lzprod_root, 'requests.db'),
                        help="URL for the requests DB. Note can use the prefix 'mysql+pymysql://' if you have a problem with MySQLdb.py [default: %(default)s]")
    args = parser.parse_args()

    # Add the python src path to the sys.path for future imports
    sys.path = [os.path.join(lzprod_root, 'src', 'python')] + sys.path

    Requests = importlib.import_module('services.RequestsDB').Requests
    sqlalchemy_utils = importlib.import_module('sqlalchemy_utils')


    sqlalchemy_utils.create_db(args.dburl)
    daemon = Daemonize(app=os.path.splitext(os.path.basename(__file__))[0],
                       pid=args.pid_file,
                       action=monitor_requests(args.dburl))
    daemon.start()
