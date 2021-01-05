from gevent import Greenlet, monkey; monkey.patch_all()


from gevent.queue import Queue

from stablehotstuff.stablehotstuff import Hotstuff
from typing import List, Callable
import os
import pickle
from gevent.event import Event
from myexperiements.sockettest.make_random_tx import tx_generator
from coincurve import PrivateKey, PublicKey

def load_key(id, N):

    with open(os.getcwd() + '/keys-' + str(N) + '/' + 'sPK.key', 'rb') as fp:
        sPK = pickle.load(fp)

    with open(os.getcwd() + '/keys-' + str(N) + '/' + 'sPK1.key', 'rb') as fp:
        sPK1 = pickle.load(fp)

    sPK2s = []
    for i in range(N):
        with open(os.getcwd() + '/keys-' + str(N) + '/' + 'sPK2-' + str(i) + '.key', 'rb') as fp:
            sPK2s.append(PublicKey(pickle.load(fp)))

    with open(os.getcwd() + '/keys-' + str(N) + '/' + 'ePK.key', 'rb') as fp:
        ePK = pickle.load(fp)

    with open(os.getcwd() + '/keys-' + str(N) + '/' + 'sSK-' + str(id) + '.key', 'rb') as fp:
        sSK = pickle.load(fp)

    with open(os.getcwd() + '/keys-' + str(N) + '/' + 'sSK1-' + str(id) + '.key', 'rb') as fp:
        sSK1 = pickle.load(fp)

    with open(os.getcwd() + '/keys-' + str(N) + '/' + 'sSK2-' + str(id) + '.key', 'rb') as fp:
        sSK2 = PrivateKey(pickle.load(fp))

    with open(os.getcwd() + '/keys-' + str(N) + '/' + 'eSK-' + str(id) + '.key', 'rb') as fp:
        eSK = pickle.load(fp)

    return sPK, sPK1, sPK2s, ePK, sSK, sSK1, sSK2, eSK


class HotstuffBFTNode (Hotstuff):

    def __init__(self, sid, id, S, T, Bfast, Bacs, N, f, recv_queue: Queue, send_queues: List[Queue], ready: Event, stop: Event, K=3, mode='debug', mute=False, tx_buffer=None):
        self.sPK, self.sPK1, self.sPK2s, self.ePK, self.sSK, self.sSK1, self.sSK2, self.eSK = load_key(id, N)

        def make_send():
            def send(j, o):
                if j == -1:
                    for _ in range(N):
                        send_queues[_].put_nowait(o)
                else:
                    send_queues[j].put_nowait(o)

            return send

        self.send = make_send()
        self.recv = lambda: recv_queue.get()
        self.ready = ready
        self.stop = stop
        self.mode = mode
        Hotstuff.__init__(self, sid, id, max(S, 200), max(int(Bfast), 1), N, f, self.sPK, self.sSK, self.sPK1, self.sSK1, self.sPK2s, self.sSK2, self.ePK, self.eSK, send=None, recv=None, K=K, mute=mute)

    def prepare_bootstrap(self):
        self.logger.info('node id %d is inserting dummy payload TXs' % (self.id))
        tx = tx_generator(250)  # Set each dummy TX to be 250 Byte
        if self.mode == 'test' or 'debug': #K * max(Bfast * S, Bacs)
            k = 0
            for _ in range(self.K + 1):
                for r in range(max(self.FAST_BATCH_SIZE * self.SLOTS_NUM, 1)):
                    suffix = hex(self.id) + hex(r) + ">"
                    Hotstuff.submit_tx(self, tx[:-len(suffix)] + suffix)
                    k += 1
                    if r % 50000 == 0:
                        self.logger.info('node id %d just inserts 50000 TXs' % (self.id))
        else:
            pass
            # TODO: submit transactions through tx_buffer
        self.logger.info('node id %d completed the loading of dummy TXs' % (self.id))

    def run(self):

        pid = os.getpid()
        self.logger.info('node %d\'s starts to run consensus on process id %d' % (self.id, pid))

        self._send = self.send
        self._recv = self.recv

        self.prepare_bootstrap()

        self.ready.wait()

        self.run_bft()

        self.stop.set()
