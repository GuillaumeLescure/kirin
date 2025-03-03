# coding=utf-8

# Copyright (c) 2001-2015, Canal TP and/or its affiliates. All rights reserved.
#
# This file is part of Navitia,
#     the software to build cool stuff with public transport.
#
# Hope you'll enjoy and contribute to this project,
#     powered by Canal TP (www.canaltp.fr).
# Help us simplify mobility and open public transport:
#     a non ending quest to the responsive locomotion way of traveling!
#
# LICENCE: This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Stay tuned using
# twitter @navitia
# IRC #navitia on freenode
# https://groups.google.com/d/forum/navitia
# www.navitia.io

from kirin import manager
from kirin.core.model import db, RealTimeUpdate
import datetime
import logging

@manager.command
def purge_rt(nb_day_to_keep, connector):
    """
    purge table real_time_update and associate_realtimeupdate_tripupdate
    for connector 'cots' or 'gtfs-rt' with nb_day_to_keep of history
    """
    logger = logging.getLogger(__name__)
    until = datetime.date.today() - datetime.timedelta(days=int(nb_day_to_keep))
    logger.info('purge table real_time_update for %s until %s', connector, until)
    RealTimeUpdate.remove_by_connectors_until(connectors=[connector], until=until)
    db.session.commit()
