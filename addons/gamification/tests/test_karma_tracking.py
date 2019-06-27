# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo.tests import common


class TestKarmaTrackingCommon(common.SingleTransactionCase):

    def setUp(self):
        super(TestKarmaTrackingCommon, self).setUp()
        self.env['gamification.karma.tracking'].create([
            # User 2 Karma gain the first January
            {
                'user_id': 2,
                'old_value': 2500,
                'new_value': 2505,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-01 09:40:30'
            },
            {
                'user_id': 2,
                'old_value': 2505,
                'new_value': 2515,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-01 10:26:30'
            },
            {
                'user_id': 2,
                'old_value': 2515,
                'new_value': 2520,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-01 11:16:52'
            },
            {
                'user_id': 2,
                'old_value': 2520,
                'new_value': 2535,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-01 11:49:13'
            },
            {
                'user_id': 2,
                'old_value': 2535,
                'new_value': 2550,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-01 12:36:41'
            },
            {
                'user_id': 2,
                'old_value': 2550,
                'new_value': 2560,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-01 13:08:25'
            },
            # User 1 Karma gain the first January
            {
                'user_id': 1,
                'old_value': 2500,
                'new_value': 2510,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-01 12:43:10'
            },
            {
                'user_id': 1,
                'old_value': 2510,
                'new_value': 2525,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-01 13:26:45'
            },
            {
                'user_id': 1,
                'old_value': 2525,
                'new_value': 2550,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-01 14:17:52'
            },
            {
                'user_id': 1,
                'old_value': 2550,
                'new_value': 2560,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-01 16:13:21'
            },
            {
                'user_id': 1,
                'old_value': 2560,
                'new_value': 2565,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-01 16:36:47'
            },
            {
                'user_id': 1,
                'old_value': 2565,
                'new_value': 2575,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-01 17:58:23'
            },
            {
                'user_id': 1,
                'old_value': 2575,
                'new_value': 2580,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-01 19:46:47'
            },
            {
                'user_id': 1,
                'old_value': 2580,
                'new_value': 2590,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-01 21:12:23'
            },
            # User 2 Karma gain the second day of January
            {
                'user_id': 2,
                'old_value': 2560,
                'new_value': 2565,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-02 10:32:14'
            },
            {
                'user_id': 2,
                'old_value': 2565,
                'new_value': 2575,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-02 11:26:41'
            },
            {
                'user_id': 2,
                'old_value': 2575,
                'new_value': 2590,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-02 12:31:52'
            },
            {
                'user_id': 2,
                'old_value': 2590,
                'new_value': 2605,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-02 13:14:13'
            },
            {
                'user_id': 2,
                'old_value': 2605,
                'new_value': 2610,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-02 15:46:23'
            },
            {
                'user_id': 2,
                'old_value': 2610,
                'new_value': 2620,
                'consolidation_type': 'none',
                'tracking_date': '2019-01-02 16:08:45'
            },
        ])


class TestKarmaTrackingCron(TestKarmaTrackingCommon):

    def test_daily_consolidation(self):
        karma_tracking = self.env['gamification.karma.tracking']
        karma_tracking._process_consolidate(datetime(2019, 1, 1, 0, 0, 0),
                                            datetime(2019, 1, 2, 0, 0, 0),
                                            'none', 'daily', '%Y-%m-%d')
        user1_record = karma_tracking.search([('user_id', '=', 1),
                                              ('old_value', '=', 2500),
                                              ('new_value', '=', 2590),
                                              ('consolidation_type', '=', 'daily'),
                                              ('tracking_date', '=', '2019-01-01 00:00:00')])
        self.assertTrue(user1_record.exists(), "Record doesn't exist.")
        user2_record = karma_tracking.search([('user_id', '=', 2),
                                        ('old_value', '=', 2500),
                                        ('new_value', '=', 2560),
                                        ('consolidation_type', '=', 'daily'),
                                        ('tracking_date', '=', '2019-01-01 00:00:00')])
        self.assertTrue(user2_record.exists(), "Record doesn't exist.")
        records = karma_tracking.search([('consolidation_type', '=', 'none'),
                                         ('tracking_date', '>=', '2019-01-01 00:00:00'),
                                         ('tracking_date', '<', '2019-01-02 00:00:00'),
                                         '|', ('user_id', '=', 2),
                                         ('user_id', '=', 1)])
        self.assertTrue(not records.exists(), "There is still records that should have been deleted.")

    def test_monthly_consolidation(self):
        karma_tracking = self.env['gamification.karma.tracking']
        # We first need to process the second day of January
        karma_tracking._process_consolidate(datetime(2019, 1, 2, 0, 0, 0),
                                            datetime(2019, 1, 3, 0, 0, 0),
                                            'none', 'daily', '%Y-%m-%d')
        karma_tracking._process_consolidate(datetime(2019, 1, 1, 0, 0, 0),
                                            datetime(2019, 2, 1, 0, 0, 0),
                                            'daily', 'monthly', '%Y-%m-01')
        user1_record = karma_tracking.search([('user_id', '=', 1),
                                              ('old_value', '=', 2500),
                                              ('new_value', '=', 2590),
                                              ('consolidation_type', '=', 'monthly'),
                                              ('tracking_date', '=', '2019-01-01 00:00:00')])
        self.assertTrue(user1_record.exists(), "Record doesn't exist.")
        user2_record = karma_tracking.search([('user_id', '=', 2),
                                              ('old_value', '=', 2500),
                                              ('new_value', '=', 2620),
                                              ('consolidation_type', '=', 'monthly'),
                                              ('tracking_date', '=', '2019-01-01 00:00:00')])
        self.assertTrue(user2_record.exists(), "Record doesn't exist.")
        records = karma_tracking.search([('consolidation_type', '=', 'daily'),
                                         ('tracking_date', '>=', '2019-01-01 00:00:00'),
                                         ('tracking_date', '<', '2019-02-01 00:00:00'),
                                         '|', ('user_id', '=', 2),
                                         ('user_id', '=', 1)])
        self.assertTrue(not records.exists(), "There is still records that should have been deleted.")
