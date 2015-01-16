# !/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlalchemy.orm import load_only
from inbox.models import Message
from inbox.models.session import session_scope

import lxml.html
import textwrap
from BeautifulSoup import BeautifulSoup as bs
import html2text
import sys

from talon.quotations import extract_from_html, register_xpath_extensions

register_xpath_extensions()

def strip_quotes(msg_body):
    placeholder = lxml.html.fromstring('<div class="nilas-elision"></div>')
    msg_body = extract_from_html(msg_body, placeholder)
    return msg_body

def reparse_message(namespace_id, message_id):
    with session_scope() as db_session:
        message = db_session.query(Message) \
            .filter(Message.namespace_id == namespace_id) \
            .filter(Message.id == message_id) \
            .options(load_only(Message.sanitized_body))
        if message:
            message = message.first()
            original_body = message.sanitized_body
            stripped_body = strip_quotes(original_body)
            return (original_body, stripped_body)
        else:
            return None

def find_message_by_subject(subject):
    with session_scope() as db_session:
        query = db_session.query(Message).filter(Message.subject == subject)
        if query:
            return query.first().id

def pretty_print(html, remove_breaks=True):
    if remove_breaks:
        html = html.replace('<br>', '')
        html = html.replace('<br />', '')
    soup = bs(html)
    return soup.prettify()

def print_side_by_side(texta, textb, MAXWIDTH=150):
    texta = texta.encode('utf8')
    textb = textb.encode('utf8')
    SPLITTER = '  |  '
    def smart_wrap(text, width):
        return [item for sublist in [textwrap.wrap(t, width) for t in text.splitlines()] for item in sublist]
    def pad(lines, width):
        for i in xrange(len(lines)):
            if len(lines[i]) < width:
                lines[i] = lines[i] + ' '*(width - len(lines[i]))
        return lines

    width = min(max([1] + [ len(l) for l in texta.splitlines() + textb.splitlines()]), MAXWIDTH)

    linesa = pad(smart_wrap(texta, width), width)
    linesb = pad(smart_wrap(textb, width), width)

    while linesa:
        if linesb:
            print linesa.pop(0) + SPLITTER +  linesb.pop(0)
        else:
            print linesa.pop(0) + SPLITTER
    while linesb:
        print ' '*width + SPLITTER + linesb.pop(0)


def pretty_height(html, remove_breaks=True):
    if remove_breaks:
        html = html.replace('<br>', '')
        html = html.replace('<br />', '')
    soup = bs(html)
    prettified = soup.prettify()
    return len(prettified.splitlines())

def examine_by_id(i, html=False):
    (original, stripped) = reparse_message(1, i)
    if html:
        print_side_by_side(pretty_print(original), pretty_print(stripped))
    else:
        h = html2text.HTML2Text()
        h.body_width = 0
        print_side_by_side(h.handle(original), h.handle(stripped))

def evaluate_labels(labels):
    false_positives = []
    false_negatives = []
    for i in labels:
        (orig, stripped) = reparse_message(1, i)
        if labels[i] == 'u':
            if orig == stripped:
                print '.'
            else:
                false_positives.append(i)
                print 'P', i
        if labels[i] == 'a':
            if orig == stripped:
                false_negatives.append(i)
                print 'N', i
            else:
                print '.'
    print 'False positives:', false_positives
    print 'False negatives', false_negatives

def examine_and_label_interactively(examples, examples_with_labels={}):
    examples.reverse()
    labels = {}
    if examples:
        i = examples.pop(-1)
    else:
        i = 1
    while True:
        k = raw_input('Considering %s: ' % i)
        if k == 'q':
            break
        elif k == 'p':
            print '\n\n----------------------- %s ----------------------------\n\n' % i
            examine_by_id(i, html=False)
        elif k == 'h':
            print '\n\n----------------------- %s ----------------------------\n\n' % i
            examine_by_id(i, html=True)
        elif k == '':
            if examples:
                i = examples.pop(-1)
        elif k == 'a':
            labels[i] = 'a'
        elif k == 'u':
            labels[i] = 'u'
        elif k == 'subject':
            subject = raw_input('Enter subject: ')
            msg_id = find_message_by_subject(subject)
            if msg_id:
                examples.append(msg_id)
        elif k == 'eval':
            evaluate_labels(examples_with_labels)
        else:
            examples.append(k)
    return labels

if __name__ == "__main__":
    examples_with_labels = {}
    if len(sys.argv) == 3:
        examples = range(int(sys.argv[1]),int(sys.argv[2]))
    else:
        examples = []

    print '\n\n--------------\n\n'
    print 'Welcome to the interactive quote stripping evaluator:'
    print '---------------------------------------------------'
    print 'NUM to go to message by id.\nsubject to goto message by subject\np to examine plaintext\nh to examine html\nq to quit'
    print 'op to examine plaintext by original algorithm'
    print 'hp to examine html by original algorithm'
    print 'u to mark a message as should be unaltered\na to mark a message should be altered'
    print 'u to mark a message as should be unaltered\na to mark a message should be altered'
    print 'ENTER to go to next message in id queue'
    print 'eval to run test on labeled examples'
    print 'orig to run test on labeled examples with original algorithm'
    raw_input('[Enter to start]')
    labels = examine_and_label_interactively(examples, examples_with_labels)
    print 'The following examples were given a label:'
    print labels


