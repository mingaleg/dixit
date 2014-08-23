#!/usr/bin/env python2
#-*- coding: utf-8 -*-

from os import path as op

import tornado.web
from tornadio2 import SocketConnection, event, TornadioRouter, SocketServer

import random

ROOT = op.normpath(op.dirname(__file__))
PASSWD = 'abacaba'
ON_HAND = 6
BONUS = 3
PENALTY = -2


cards = [str(i+1) + '.png' for i in range(344)]
used = []
random.shuffle(cards)
queue = []


class IndexHandler(tornado.web.RequestHandler):
    """Index page rendering"""
    def get(self):
        self.render("index.html")

class DixitConnection(SocketConnection):
    """Dixit player connection class"""
    participants = {}
    game_status = 'break'
    round_master = None
    description = ''
    choices = []
    votes = {}
    permutation = []
    reversed_cards = {}
    variants = None

    def broadcast(self, msg, mtype = 'message', back = True):
        """Send message to all participants
        msg: Message
        mtype: Message type
        back: """
        for p in DixitConnection.participants:
            if back or (DixitConnection.participants[p] != self):
                DixitConnection.participants[p].emit(mtype, msg)

    def on_open(self, *args, **kwargs):
        self.nickname = ''
        self.master = False
        self.score = 0
        self.cards = []
        self.is_round_master = False
        self.my_card = None
        self.my_vote = None
        self.vote_cnt = 0
        self.diff = 0
        self.closed = False

    def on_close(self, *args, **kwargs):
        self.logout()
        
    @event('logout')
    def logout(self):
        print('Closed connection')
        if DixitConnection.game_status == 'break':
            if self.nickname:
                del DixitConnection.participants[self.nickname]
                self.total_update_scoreboard()


    @event('nick')
    def change_nick(self, nick):
        if DixitConnection.game_status != 'break':
            self.emit('error', {
                'command': 'nick',
                'status': 'FAIL',
                'comment': 'Nick change is only allowed during the break',
            })
            return
        if not nick:
            self.emit('error', {
                'command': 'nick',
                'status': 'FAIL',
                'comment': 'Nick should be non-zero',
            })
            return
        if nick in DixitConnection.participants:
            self.emit('error', {
                'command': 'nick',
                'status': 'FAIL',
                'comment': 'Name is alredy used: %s' % nick,
            })
            return
        if self.nickname:
            DixitConnection.participants[nick] = DixitConnection.participants[self.nickname]
            del DixitConnection.participants[self.nickname]
        else:
            DixitConnection.participants[nick] = self
            self.nickname = nick
        self.emit('nick', nick)
        self.emit('system', 'Welcome, %s' % nick)
        self.broadcast('New participant: <b>%s</b>' % nick, 'system', False)
        self.total_update_scoreboard()
        self.update_cards()
        queue.append(self)

    @event('become_master')
    def become_master(self, passwd):
        if self.master:
            self.emit('error', {
                'command': 'master',
                'status': 'WARNING',
                'comment': 'You are alredy master',
            })
            return
        if passwd == PASSWD:
            self.master = True
            self.emit('master', True)
        else:
            self.emit('error', {
                'command': 'master',
                'status': 'FAIL',
                'comment': 'Wrong pass',
            })
            return
        self.broadcast('%s is master' % self.nickname, 'system', False)

    def total_update_scoreboard(self):
        lst = []
        for x in DixitConnection.participants:
            lst.append([DixitConnection.participants[x].nickname, DixitConnection.participants[x].score])
        lst.sort(key = lambda x: (-x[1], x[0]))
        for foo in DixitConnection.participants:
            DixitConnection.participants[foo].emit('update_scoreboard', lst)

    @event('update_scoreboard')
    def update_scoreboard(self):
        lst = []
        for x in DixitConnection.participants:
            lst.append([DixitConnection.participants[x].nickname, DixitConnection.participants[x].score])
        lst.sort(key = lambda x: (-x[1], x[0]))
        self.emit('update_scoreboard', lst)

    @event('update_cards')
    def update_cards(self):
        while len(self.cards) < ON_HAND:
            global cards
            if len(cards) == 0:
                self.broadcast('Finished deck, reloading', 'system')
                global used
                cards = used
                used = []
                random.shuffle(cards)
            self.cards += [cards.pop(0)]
        self.emit('update_cards', self.cards)

    @event('start_round')
    def start_round(self):
        if not self.master:
            self.emit('error', {
                'command': 'round',
                'status': 'FAIL',
                'comment': 'Only master can starts round',
            })
            return
        if DixitConnection.game_status != 'break':
            self.emit('error', {
                'command': 'round',
                'status': 'FAIL',
                'comment': 'Game_status should be "break" but it is "%s"'% DixitConnection.game_status,
            })
            return
        for x in DixitConnection.participants:
            DixitConnection.participants[x].update_cards()
        DixitConnection.round_master = queue[0]
        queue.append(queue.pop(0))
        DixitConnection.round_master.is_round_master = True
        DixitConnection.game_status = 'roundmaster_turn'
        print('Game status: %s' % DixitConnection.game_status)
        print('Round master: %s' % DixitConnection.round_master.nickname)
        DixitConnection.choices = {}

        for x in DixitConnection.participants:
            DixitConnection.participants[x].emit('start_round', {
                'round_master': DixitConnection.round_master.nickname,
                'is_round_master': DixitConnection.round_master.nickname == DixitConnection.participants[x].nickname,
            })

        self.broadcast('New round: %s is master' % DixitConnection.round_master.nickname, 'system')

    @event('roundmaster_turn')
    def roundmaster_turn(self, description, card):
        DixitConnection.description = description
        if DixitConnection.game_status != 'roundmaster_turn':
            self.emit('error', {
                'command': 'roundmaster_turn',
                'status': 'FAIL',
                'comment': 'Now it is not roundmaster turn',
                'minor_info': 'game_status: %s' % DixitConnection.game_status,
            })
            return
        if not self.is_round_master:
            self.emit('error', {
                'command': 'roundmaster_turn',
                'status': 'FAIL',
                'comment': 'You are not roundmaster',
            })
            return
        if card not in self.cards:
            self.emit('error', {
                'command': 'roundmaster_turn',
                'status': 'FAIL',
                'comment': 'You have no such card: %s'% card,
            })
            return        
        DixitConnection.choices = [[self, card]]
        self.cards.remove(card)
        self.my_card = card
        DixitConnection.reversed_cards[card] = self

        self.emit('system', "Ok choose done")

        DixitConnection.game_status = 'common_turn'

        self.broadcast('<b><u>Association</u></b>: %s' % description, 'system')

        for foo in DixitConnection.participants:
            DixitConnection.participants[foo].emit('common_turn', {
                'cards': DixitConnection.participants[foo].cards,
                'description': DixitConnection.description,
                'is_round_master': DixitConnection.participants[foo].is_round_master,
            })

        self.broadcast_choices_status()

    def broadcast_choices_status(self):
        if DixitConnection.game_status in ['roundmaster_turn', 'common_turn']:
            choosers = list(map(lambda x: x.nickname, zip(*DixitConnection.choices)[0]))
        elif DixitConnection.game_status in ['vote_stage']:
            choosers = DixitConnection.votes.keys()
        else:
            choosers = []
        choices_status = \
                dict(map(
                    lambda x: (x, x in choosers), 
                    DixitConnection.participants
                ))
        for foo in DixitConnection.participants:
            DixitConnection.participants[foo].emit('choices_status', choices_status)


    @event('choice')
    def choice(self, card):
        if self in zip(*DixitConnection.choices)[0]:
            self.emit('error', {
                'command': 'choice',
                'status': 'FAIL',
                'comment': 'You have alredy selected',
            })
            return
        if card not in self.cards:
            self.emit('error', {
                'command': 'choice',
                'status': 'FAIL',
                'comment': 'You have no such card: %s' % card,
            })
            return
        DixitConnection.choices.append([self, card])
        self.my_card = card
        DixitConnection.reversed_cards[card] = self
        self.cards.remove(card)
        self.emit('choice', {
            'cards': self.cards,
        })

        self.broadcast_choices_status()

        if len(DixitConnection.choices) == len(DixitConnection.participants):
            DixitConnection.permutation = list(range(len(DixitConnection.choices)))
            random.shuffle(DixitConnection.permutation)
            DixitConnection.reversed_cards = [0] * len(DixitConnection.permutation)
            for i in range(len(DixitConnection.permutation)):
                DixitConnection.reversed_cards[DixitConnection.permutation[i]] = i
            DixitConnection.reversed_cards = dict(map(
                lambda x: (DixitConnection.choices[x][1], DixitConnection.choices[x][0]), 
                DixitConnection.reversed_cards)
            )

            DixitConnection.variants = [DixitConnection.choices[i][1] for i in DixitConnection.permutation]

            for foo in DixitConnection.participants:
                DixitConnection.participants[foo].emit('vote_stage', {
                    'is_round_master': DixitConnection.participants[foo].is_round_master,
                    'variants': DixitConnection.variants,
                })
            DixitConnection.game_status = 'vote_stage'
            DixitConnection.votes = {}
            self.broadcast_choices_status()

    @event('vote')
    def vote(self, vote):
        if self.is_round_master:
            self.emit('error', {
                'command': 'vote',
                'status': 'FAIL',
                'comment': 'You are roundmaster',
            })
            return
        if self.nickname in DixitConnection.votes:
            self.emit('error', {
                'command': 'vote',
                'status': 'FAIL',
                'comment': 'You have alredy voted',
            })
            return
        if vote == list(filter(lambda x: x[0].nickname == self.nickname, DixitConnection.choices))[0][1]:
            self.emit('error', {
                'command': 'vote',
                'status': 'FAIL',
                'comment': 'Сan not vote for yourself',
            })
            return
        vote = DixitConnection.reversed_cards[vote]
        self.my_vote = vote
        vote.vote_cnt += 1

        DixitConnection.votes[self.nickname] = vote
        self.emit('vote')
        self.broadcast_choices_status()
        if len(DixitConnection.votes) == len(DixitConnection.participants) - 1:
            for nick, user in DixitConnection.participants.iteritems():
                user.diff = 0

            if DixitConnection.round_master.vote_cnt in [0, len(DixitConnection.participants) - 1]:
                DixitConnection.round_master.diff = PENALTY
            else:
                for nick, user in DixitConnection.participants.iteritems():
                    if user.is_round_master:
                        user.diff += BONUS
                    else:
                        if user.my_vote.is_round_master:
                            user.diff += BONUS
                        user.diff += user.vote_cnt

            report = '<b>Round results:</b><br/>'
            for nick, user in DixitConnection.participants.iteritems():
                report += '<b>%s%s</b>: %d points<br/>' % (nick, (' (master)' if user.is_round_master else ''), user.diff)
                user.score += user.diff

            self.broadcast(report, "results")

            cards_results = []
            for nick, user in DixitConnection.participants.iteritems():
                cards_results.append({
                    'card': user.my_card,
                    'cnt': user.vote_cnt,
                    'master': user.is_round_master,
                    'owner': user.nickname,
                })


            for foo in DixitConnection.participants:
                if not DixitConnection.participants[foo].is_round_master:
                    DixitConnection.participants[foo].emit('break', {
                        'master_card': DixitConnection.round_master.my_card,
                        'my_card': DixitConnection.participants[foo].my_card,
                        'my_vote': DixitConnection.participants[foo].my_vote.my_card,
                        'round_master': False,
                        'variants': cards_results,
                    })
                else:
                    DixitConnection.participants[foo].emit('break', {
                        'master_card': DixitConnection.round_master.my_card,
                        'my_card': DixitConnection.participants[foo].my_card,
                        'round_master': True,
                        'variants': cards_results,
                    })
            global used
            for foo in DixitConnection.choices:
                used += [foo[1]]
            self.total_update_scoreboard()
            DixitConnection.game_status = 'break'
            for nick, user in DixitConnection.participants.iteritems():
                user.is_round_master = False
                user.my_card = None
                user.my_vote = None
                user.vote_cnt = 0
                user.diff = 0
            self.broadcast_choices_status()

    @event('message')
    def message(self, message):
        if self.nickname == '':
            self.emit('error', {
                'command': 'message',
                'status': 'FAIL',
                'comment': 'You should login first',
            })
            return
        self.broadcast('<b>%s</b>: %s' % (self.nickname, message))

    def on_message(self, message):
        pass




router = TornadioRouter(DixitConnection, {
    'enabled_protocols': [
        'websocket',
        'flashsocket',
        'xhr-multipart',
        'xhr-polling'
    ]
})

print(dir(router))

#configure the Tornado application
application = tornado.web.Application(
    router.apply_routes([
        (r"/", IndexHandler), 
        (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": op.join(ROOT, 'static')})
    ]),
    flash_policy_port = 843,
    flash_policy_file = op.join(ROOT, 'flashpolicy.xml'),
    socket_io_port = 8001
)

#application = tornado.web.Application(router.urls, socket_io_port=8001)

if __name__ == "__main__":
    import logging
    logging.getLogger().setLevel(logging.DEBUG)

    SocketServer(application)
