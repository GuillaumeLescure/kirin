# COTS Connector

## Overview
Realtime information for long distance trains of the SNCF network is received in a COTS stream.
This document describes how a COTS realtime stream is modeled in Kirin.

## Input data description
A realtime COTS stream is obtained as a JSON file via a message queue mechanism.
Each feed message represents an update on the information about a whole train (its status, the
associated delay, causes, etc.). An example of a delayed train is provided
[here](../tests/fixtures/cots_train_96231_delayed.json).

The information concerning the displayed messages related to train modifications is referenced in a
separate stream provided by an external web service called *parametreLIV*.
The latter returns a [text message](../tests/fixtures/motif-retard.json) for all available
situations associated with an id referenced in the COTS stream.
- In case of non availability of the web service, no message is registered.
- For each message object, only the attributes `id` and `labelExt` are used.
- In case of two messages referenced by the same id, the last one in the list is taken into account.

## Connector description
This document doesn't describe all the fields of the Kirin model. Only COTS relevant fields are
described below. For example, the id field of a `RealTimeUpdate` is managed by Kirin and is not
detailed in the present specification.

### RealTimeUpdate
Kirin property | COTS object | Comment/Mapping rule
--- | --- | ---
connector |  | Fixed value `cots`.
raw_data | _Complete received feed_ | 
contributor |  | Fixed value specified in the configuration of Kirin.
trip_updates |  | List of trip updates information, see `TripUpdates` below.

### TripUpdate
A COTS feed can udpate more than one `VehicleJourney`, see below for the mapping method.

Kirin property | COTS object | Comment/Mapping rule
--- | --- | ---
vj_id |  | Id of the `VehicleJourney` in Navitia updated by this `TripUpdate`. See below for the mapping method.
status | *nouvelleVersion/statutOperationnel* | Status is set to `add` when value is `AJOUTEE`, `delete` when value is `SUPPRIMEE`, and `update` in every other case.
message | *nouvelleVersion/idMotifInterneReference* | Reference to the field `labelExt` of the *parametreLIV* feed having the same `id`. If no matching `id` is found, the message is left empty.
contributor |  | Fixed value specified in the configuration of Kirin.
company_id | *nouvelleVersion/codeCompagnieTransporteur* | Id of the transport operator that runs the `VehicleJourney` in Navitia. If no associated operator is found in Navitia, then the id of the SNCF is used by default. See below for the mapping method.
stop_time_updates |  | List of arrival/departure time updates at stops for this trip, see `StopTimeUpdates` below.
effect |  | See below for the mapping method.
physical_mode_id | *nouvelleVersion/indicateurFer* | Id of the physical mode associated with the `VehicleJourney` in Navitia. See below for the mapping method.

**Setting the trip effect**

Effect is set to `ADDITIONAL_SERVICE` when the trip status is `add` and `NO_SERVICE` when the trip
status is `delete`.

Otherwise, the trip effect is calculated based on the statuses at the stops of the Trip in the
following order:
* the effect is set to `DETOUR`, when the status at some stops is `added_for_detour` or `delete_for_detour`
* otherwise, the effect is set to `REDUCED_SERVICE`, when the status at some stop is `delete`
* otherwise, the effect is set to `MODIFIED_SERVICE`, when the status at some stop is `add`
* otherwise, the effect is set to `SIGNIFICANT_DELAYS`, when the status at some stop is `update`
* otherwise, the effect is set to `UNKNOWN_EFFECT`.

### VehicleJourney
#### Searching for corresponding VehicleJourneys in Navitia
Getting the right trips from Navitia impacted by a COTS stream is not straightforward.
Finding those `VehicleJourney` implies using:
* *nouvelleVersion/numeroCourse* : Train number, may be a secondary number referenced at the stop level
* *nouvelleVersion/indicateurFer* : Indication whether the impacted vehicle is a train (value `FERRE`) or a coach (otherwise)
* *nouvelleVersion/codeCompagnieTransporteur* : Code of the company operating the vehicle
* the date of the trip is included in the `dateHeure` properties below

To narrow down the research, departure/arrival times at stops are also used.
The COTS stream references passing stops, however only stations must be taken into account.
Stops are listed in *nouvelleVersion/listePointDeParcours*, a `station` should have the
`typeArret` property set to `CD`, `CH`, `FD`, `FH` or an empty value.

The time frame used for Navitia's VehicleJourney is defined by :
* *horaireVoyageurDepart/dateHeure* of the first `station` minus 1 hour
* *horaireVoyageurArrivee/dateHeure* of the last `station` plus 1 hour

When base_schedule information is modified with adapted data (when a strike is scheduled or in
progress for example), the COTS stream should be applied to this updated trip.

**Use of *nouvelleVersion/indicateurFer***

In case of an updated trip, *nouvelleVersion/indicateurFer* should be used to narrow the research
to rail or road trips in Navitia. All the physical modes in Navitia are listed in
[NTFS specifications](https://github.com/CanalTP/navitia/blob/dev/documentation/ntfs/ntfs_fr.md#physical_modestxt-requis).

When *nouvelleVersion/indicateurFer* is set to `FERRE`, use only corresponding physical
modes : LocalTrain, LongDistanceTrain, Metro, RapidTransit, RailShuttle, Train, Tramway.
Otherwise, the previously listed modes should be removed.

In case of a trip addition, when the *nouvelleVersion/indicateurFer* is set to `FERRE`, the
default physical mode is `Train`. Otherwise, the COTS stream is ignored.
The creation of road trips will be covered in a later version of the connector.

**Use of *nouvelleVersion/codeCompagnieTransporteur***

The operator associated to the considered Navitia trips should have a complementary code of type
`RefProd` that matches the value of *nouvelleVersion/codeCompagnieTransporteur*.
If the field is empty in the COTS stream, then the value `1187` that corresponds to the SNCF
operator is used.

#### Creating a new VehicleJourney for Navitia
In case of a trip addition (trip status is set to `add`), a complete `VehicleJourney` needs to be
sent to Navitia using the available information in the COTS stream.
* The new trip is associated with the SNCF operator.
* The trip headsign is specified by the train number in *nouvelleVersion/numeroCourse*.
* The physical mode is set to `Coach` when the value of *nouvelleVersion/indicateurFer* is `ROUTIER`, otherwise the physical mode is set to `LongDistanceTrain`.
* A new dataset `realtime.cots` must be created in Navitia (if it does not already exist) to be linked with the new trip. This dataset is attached to the SNCF contributor found in Navitia.
* A new service is created in Navitia to be attached to the new trip. This service is valid on the date specified by the departure date of the trip.
* The new trip is attached to a new route named after the origin and destination stops (if such a route does not already exist).
* The new route is attached to a new line (if it does not already exist). The line name is also taken after the origin and destination stops (same as the route name).

Ideas to explore and validate:
* The commercial mode of the new line is determined based on the value of *nouvelleVersion/codeMarqueTransporteur*. When the value is `TER`, if the *nouvelleVersion/indicateurFer* is `FERRE`, then the commercial mode is set to `Train TER`. In case of a new road trip, the commercial mode is set to `Car TER`. In all other cases, the commercial mode is set after the value of *nouvelleVersion/codeMarqueTransporteur*.

#### Recording the VehicleJourneys 
Each `VehicleJourney` found in Navitia corresponding to the COTS stream is recorded, so that they
are all impacted.

Kirin property | Comment/Mapping rule
--- | ---
navitia_trip_id | `trip_id` of the VehicleJourney in Navitia. See above for the mapping rule.
start_timestamp | Start datetime of the `VehicleJourney` in Navitia.

### StopTimeUpdate
Note that if, for a given trip, a station in the COTS stream cannot be mapped to a `stop_time` in
the corresponding `VehicleJourney` in Navitia, then the station is ignored, unless the stop_time
is created.

Kirin property | COTS object | Comment/Mapping rule
--- | --- | ---
order |  | `stop_time` order of this stop in the `VehicleJourney`. The order must respect the *rang* of each stop in the COTS stream.
stop_id |  | Id of this stop in Navitia
message | *idMotifInterneDepartReference* | If present, it points to the field `labelExt` of the *parametreLIV* feed having the same `id`. Otherwise, the value of *idMotifInterneArriveeReference* is used as reference. If no matching `id` is found, the message is left empty.
departure |  | Departure datetime of the `VehicleJourney` for this stop in Navitia. In case of a stop addition, the departure time is set to *horaireVoyageurDepart/dateHeure* if no delay is specified for this new stop or to the computed value *horaireVoyageurDepart/dateHeure + horaireProjeteDepart/pronosticIV* otherwise.
departure_delay | *listeHoraireProjeteDepart/pronosticIV* | See the mapping method below.
departure_status | *horaireVoyageurDepart/statutCirculationOPE* | See the mapping method below.
arrival |  | Arrival datetime of the `VehicleJourney` for this stop in Navitia. In case of a stop addition, the arrival time is set to *horaireVoyageurArrivee/dateHeure* if no delay is specified for this new stop or to the computed value *horaireVoyageurArrivee/dateHeure + horaireProjeteArrivee/pronosticIV* otherwise.
arrival_delay | *listeHoraireProjeteArrivee/pronosticIV* | See the mapping method below.
arrival_status | *horaireVoyageurArrivee/statutCirculationOPE* | See the mapping method below.

**Setting the departure_delay and arrival_delay property**

For the **departure_delay** :
* In case of a stop addition, no delay is considered. If *listeHoraireProjeteDepart* is defined, the value of *pronosticIV* is ignored for this field since it is used to compute the departure datetime.
* If the *sourceHoraireProjeteDepartReference* is not defined (or contains an empty value)
  * If *listeHoraireProjeteDepart* is not defined (or empty) => the train is considered on time
  * If there is only one item in the *listeHoraireProjeteDepart* => the value of its *pronosticIV* is used
  * Else (there are several items in the *listeHoraireProjeteDepart*) => the cots stream is considered invalid and is rejected.
* If the *sourceHoraireProjeteDepartReference* is available (and non empty value)
  * If *listeHoraireProjeteDepart* is not empty and one of the items has the same value in its *source* property as *sourceHoraireProjeteDepartReference* => the value of its *pronosticIV* is used
  * Else (empty or no item has the same *source* property as *sourceHoraireProjeteDepartReference*) => the cots stream is considered invalid and is rejected.

For the **arrival_delay**, the same rule applies with the *sourceHoraireProjeteArriveeReference*
property and the *listeHoraireProjeteArrivee*.

**Setting the arrival/departure status**

The departure/arrival status at a stop of the `VehicleJourney` follows the trip status when the
latter is set to `add` or `delete`. Otherwise, the status may vary depending on the
departure/arrival time updates or delays provided at the level of the station.

The departure (resp. arrival) status is resolved with regard to the field
*horaireVoyageurDepart/statutCirculationOPE* (resp. *horaireVoyageurArrivee/statutCirculationOPE*):
* status is set to `add` when the field value is `CREATION`, `added_for_detour` when the field value is `DETOURNEMENT`, `delete` when the field value is `SUPPRESSION`, `deleted_for_detour` when the field value is `SUPPRESSION_DETOURNEMENT` and `update` otherwise.
* status is set to `none` when the departure (resp. arrival) delay is set to 0 or when this is the last (resp. first) stop of the `VehicleJourney`.

Note that in case of a sequence of COTS streams concerning the same trip, added or deleted stops
always keep their statuses in the following feeds. For example, given a COTS stream specifying a
new destination for a trip (last stop with a *horaireVoyageurArrivee/statutCirculationOPE* set to
`CREATION`), if a later stream updates the delay or even adds more stops, the previously added
destination stop will still have its *horaireVoyageurArrivee/statutCirculationOPE* set to `CREATION`.
