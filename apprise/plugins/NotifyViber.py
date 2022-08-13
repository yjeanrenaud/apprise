# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 Chris Caron <lead2gold@gmail.com>
# All rights reserved.
#
# This code is licensed under the MIT License.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files(the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and / or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions :
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# API Details:
#   https://developers.viber.com/docs/api/rest-bot-api/#send-message
#
import six
import requests
from uuid import uuid4
from json import dumps

from .NotifyBase import NotifyBase
from ..common import NotifyType
from ..common import NotifyImageSize
from ..utils import parse_list
from ..URLBase import PrivacyMode
from ..AppriseLocale import gettext_lazy as _


class NotifyViber(NotifyBase):
    """
    A wrapper for Viber Notifications
    """

    # The default descriptive name associated with the Notification
    service_name = 'Viber'

    # The services URL
    service_url = 'https://viber.com/'

    # The default protocol
    protocol = 'viber'

    # The default protocol
    secure_protocol = 'viber'

    # A URL that takes you to the setup/help of the specific protocol
    setup_url = 'https://github.com/caronc/apprise/wiki/Notify_viber'

    # The Notification URL
    notify_url = 'https://chatapi.viber.com/pa/send_message'

    # Allows the user to specify the NotifyImageSize object
    image_size = NotifyImageSize.XY_256

    # We don't support titles for Signal notifications
    title_maxlen = 0

    # client version support the API version. Certain features may not work as
    # expected if set to a number that’s below their requirements.
    min_api_version = 1

    # Max length is 7000 characters
    body_maxlen = 7000

    # Define object templates
    templates = (
        '{schema}://{token}/{targets}',
        '{schema}://{user}@{token}/{targets}',
    )

    # Define our template tokens
    template_tokens = dict(NotifyBase.template_tokens, **{
        'user': {
            'name': _('Sender'),
            'type': 'string',
        },
        'token': {
            'name': _('App Key'),
            'type': 'string',
            'private': True,
        },
        'target_receiver': {
            'name': _('Target Receiver'),
            'type': 'string',
            'map_to': 'targets',
        },
        'targets': {
            'name': _('Targets'),
            'type': 'list:string',
        }
    })

    # Define our template arguments
    template_args = dict(NotifyBase.template_args, **{
        'to': {
            'alias_of': 'targets',
        },
        'image': {
            'name': _('Include Image'),
            'type': 'bool',
            'default': True,
            'map_to': 'include_image',
        },
    })

    def __init__(self, token, user=None, targets=None, include_image=True, **kwargs):
        """
        Initialize Viber Object
        """
        super(NotifyViber, self).__init__(**kwargs)

        # Store our APP Key
        self.token = token

        # Store our user if set
        self.user = self.user[0:28].strip() \
            if isinstance(user, six.string_types) else self.app_id

        # Track whether or not we want to send an image with our notification
        # or not.
        self.include_image = include_image

        # Store our targets
        self.targets = parse_list(targets)

        return

    def send(self, body, title='', notify_type=NotifyType.INFO,
             **kwargs):
        """
        Perform Viber Notification
        """

        if len(self.targets) == 0:
            # There were no services to notify
            self.logger.warning(
                'There were no Viber targets to notify.')
            return False

        # error tracking (used for function return)
        has_error = False

        # Prepare our headers
        headers = {
            'User-Agent': self.app_id,
            'Content-Type': 'application/json',
            'X-Viber-Auth-Token': self.token,
        }

        # Format defined here:
        #   https://developers.viber.com/docs/api/rest-bot-api/#send-message

        # Example:
        # {
        #    "receiver":"01234567890A=",
        #    "min_api_version":1,
        #    "sender":{
        #       "name":"John McClane",
        #       "avatar":"http://avatar.example.com"
        #    },
        #    "tracking_data":"tracking data",
        #    "type":"text",
        #    "text":"Hello world!"
        # }


        # Prepare our payload
        payload = {
            # this get's populated below int he loop
            "receiver": None,

            # Default api version
            "min_api_version": self.min_api_version,
            "sender": {
                "name": self.user if self.user else self.app_id,
            }
            'tracking_data': '{}/{}'.format(self.app_id, str(uuid4()))
            'type': 'text',
            'text': body,
        }

        if self.include_image:
            if self.avatar:
                payload['sender']["avatar"] = self.avatar

            else:
                # Acquire our image url if configured to do so
                avatar = None if not self.include_image else \
                    self.image_url(notify_type)

                if avatar:
                    payload['sender']["avatar"] = avatar

        # Create a copy of our list
        targets = list(self.targets)

        while targets:
            target = target.pop()

            self.logger.debug('Viber POST URL: %s (cert_verify=%r)' % (
                self.notify_url, self.verify_certificate,
            ))
            self.logger.debug('Viber Payload: %s' % str(payload))

            # Always call throttle before any remote server i/o is made
            self.throttle()
            try:
                r = requests.post(
                    self.notify_url,
                    data=dumps(payload),
                    headers=headers,
                    verify=self.verify_certificate,
                    timeout=self.request_timeout,
                )
                if r.status_code not in (
                        requests.codes.ok, requests.codes.created):
                    # We had a problem
                    status_str = \
                        NotifyViber.http_response_code_lookup(
                            r.status_code)

                    self.logger.warning(
                        'Failed to send {} Viber notification{}: '
                        '{}{}error={}.'.format(
                            len(self.targets[index:index + batch_size]),
                            ' to {}'.format(self.targets[index])
                            if batch_size == 1 else '(s)',
                            status_str,
                            ', ' if status_str else '',
                            r.status_code))

                    self.logger.debug(
                        'Response Details:\r\n{}'.format(r.content))

                    # Mark our failure
                    has_error = True
                    continue

                else:
                    self.logger.info(
                        'Sent {} Viber notification{}.'
                        .format(
                            len(self.targets[index:index + batch_size]),
                            ' to {}'.format(self.targets[index])
                            if batch_size == 1 else '(s)',
                        ))

            except requests.RequestException as e:
                self.logger.warning(
                    'A Connection error occured sending {} Viber '
                    'notification(s).'.format(
                        len(self.targets[index:index + batch_size])))
                self.logger.debug('Socket Exception: %s' % str(e))

                # Mark our failure
                has_error = True
                continue

        return not has_error

    def url(self, privacy=False, *args, **kwargs):
        """
        Returns the URL built dynamically based on specified arguments.
        """

        # Define any URL parameters
        params = {}
        if self.avatar:
            params['avatar'] = self.avatar

        # Extend our parameters
        params.update(self.url_parameters(privacy=privacy, *args, **kwargs))

        # Determine Authentication
        sender = ''
        if self.user:
            sender = '{user}@'.format(
                user=NotifyViber.quote(self.user, safe=''),
            )

        return '{schema}://{sender}{token}/{targets}?{params}'.format(
            schema=self.secure_protocol,
            sender=sender,
            # never encode hostname since we're expecting it to be a valid one
            token=self.pprint(
                    self.token, privacy, mode=PrivacyMode.Secret, safe=''),
            targets='/'.join(
                [NotifyViber.quote(x, safe='=') for x in self.targets]),
            params=NotifyViber.urlencode(params),
        )

    @staticmethod
    def parse_url(url):
        """
        Parses the URL and returns enough arguments that can allow
        us to re-instantiate this object.

        """

        results = NotifyBase.parse_url(url, verify_host=False)
        if not results:
            # We're done early as we couldn't load the results
            return results

        # Get our entries; split_path() looks after unquoting content for us
        # by default
        results['targets'] = \
            NotifyViber.split_path(results['fullpath'])

        # The hostname is our Application Key.  Viber also refers to this as a
        # Token too (depending on what screen you look at); but it's all the
        # same thing
        results['token'] = NotifyViber.unquote(results['host'])

        # Support the 'to' variable so that we can support targets this way too
        # The 'to' makes it easier to use yaml configuration
        if 'to' in results['qsd'] and len(results['qsd']['to']):
            results['targets'] += \
                NotifyViber.parse_list(results['qsd']['to'])

        # Include images with our message
        results['include_image'] = \
            parse_bool(results['qsd'].get('image', True))

        return results
