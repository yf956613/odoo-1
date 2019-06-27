# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class KarmaTracking(models.Model):
    _name = 'gamification.karma.tracking'
    _description = 'Track Karma Changes'

    user_id = fields.Many2one('res.users', 'User', required=True)
    old_value = fields.Integer('Old Karma Value', required=True, readonly=1)
    new_value = fields.Integer('New Karma Value', required=True, readonly=1)
    consolidation_type = fields.Selection(selection=[('none', 'Not Consolidated'),
                                                     ('daily', 'Daily Consolidated'),
                                                     ('monthly', 'Monthly Consolidated'),
                                                     ('yearly', 'Yearly Consolidated')],
                                          default='none')
    tracking_date = fields.Datetime(default=fields.Datetime.now)

    @api.model
    def _consolidate_last_day(self):
        to_date = datetime.now()
        from_date = to_date - relativedelta(days=1)
        self._process_consolidate(from_date, to_date, 'none', 'daily', '%Y-%m-%d')

    @api.model
    def _consolidate_last_month(self):
        """ When consolidating daily values in monthly values we need to do it for the month before the last one
            so that we will keep at least 30 daily values. If we immediately consolidate all daily values we won't
            be able to retrieve last week karma changes accurately.
        """
        to_date = datetime.now() - relativedelta(months=1)
        from_date = to_date - relativedelta(months=1)
        self._process_consolidate(from_date, to_date, 'daily', 'monthly', '%Y-%m-01')

    @api.model
    def _consolidate_last_year(self):
        """ Like the _consolidate_last_month we consolidate the monthly values in yearly values for the year before
            the last one.
        """
        to_date = datetime.now() - relativedelta(years=1)
        from_date = to_date - relativedelta(years=1)
        self._process_consolidate(from_date, to_date, 'monthly', 'yearly', '%Y-01-01')

    def _process_consolidate(self, from_date, to_date, old_consolidation_type, new_consolidation_type, tracking_date_format):
        """
        Consolidate all old_consolidation_type records which tracking_date is between from_date to to_date
        into one new_consolidation_type record with a new tracking_date

        :param from_date: the date from which the method will consolidate the records (included)
        :param to_date: the date until which the method will consolidate the records (excluded)
        :param old_consolidation_type: the consolidation_type of the records to consolidate
        :param new_consolidation_type: the consolidation_type of the resulting record
        :param tracking_date_format: the date format that will be used for the tracking_date of the resulting record
        :return:
        """
        select_query = """
                        SELECT user_id, MIN(old_value) as old_value, MAX(new_value) as new_value
                        FROM gamification_karma_tracking 
                        WHERE tracking_date::timestamp >= timestamp '{from_date}' 
                        AND tracking_date::timestamp < timestamp '{to_date}'
                        AND consolidation_type = '{consolidation_type}'
                        GROUP BY user_id
                        """.format(from_date=from_date, to_date=to_date, consolidation_type=old_consolidation_type)
        self.env.cr.execute(select_query)
        results = self.env.cr.dictfetchall()
        if len(results) > 0:
            for result in results:
                result['consolidation_type'] = new_consolidation_type
                result['tracking_date'] = from_date.strftime(tracking_date_format)
                self.create(result)
            delete_query = """
                            DELETE FROM gamification_karma_tracking
                            WHERE tracking_date::timestamp >= timestamp '{from_date}' 
                            AND tracking_date::timestamp < timestamp '{to_date}'
                            AND consolidation_type = '{consolidation_type}'
                            """.format(from_date=from_date, to_date=to_date, consolidation_type=old_consolidation_type)
            self.env.cr.execute(delete_query)

    def _get_total_karma(self, from_date, to_date):
        date_condition = """
                         AND tracking_date::timestamp > timestamp '{from_date}'
                         AND tracking_date::timestamp <= timestamp '{to_date}'
                         """.format(from_date=from_date, to_date=to_date)
        query = """
                SELECT user_id as id, SUM(new_value - old_value) as total_karma
                FROM gamification_karma_tracking g
                JOIN res_users u ON u.id = g.user_id 
                WHERE u.active = TRUE 
                %s
                GROUP BY user_id
                ORDER BY total_karma DESC
                """ % (date_condition if from_date else "")

        self.env.cr.execute(query)
        results = self.env.cr.dictfetchall()
        return results
