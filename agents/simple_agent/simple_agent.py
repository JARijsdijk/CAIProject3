import logging
from time import time
from typing import cast

from geniusweb.actions.Accept import Accept
from geniusweb.actions.Action import Action
from geniusweb.actions.Offer import Offer
from geniusweb.actions.PartyId import PartyId
from geniusweb.bidspace.AllBidsList import AllBidsList
from geniusweb.inform.ActionDone import ActionDone
from geniusweb.inform.Finished import Finished
from geniusweb.inform.Inform import Inform
from geniusweb.inform.Settings import Settings
from geniusweb.inform.YourTurn import YourTurn
from geniusweb.issuevalue.Bid import Bid
from geniusweb.issuevalue.Domain import Domain
from geniusweb.party.Capabilities import Capabilities
from geniusweb.party.DefaultParty import DefaultParty
from geniusweb.profile.utilityspace.LinearAdditiveUtilitySpace import (
    LinearAdditiveUtilitySpace,
)
from geniusweb.profileconnection.ProfileConnectionFactory import (
    ProfileConnectionFactory,
)
from geniusweb.progress import Progress


class SimpleAgent(DefaultParty):
    """
    Sends offers in descending order of utility
    Accepts when an offer is received with utility that is at least equal to the utility of the next bid,
    or if the time progressed has passed the 95% mark and the received offer has a utility at least equal to the reserve
    """

    def __init__(self):
        super().__init__()

        # Attributes to be obtained from a Settings message:
        self.me: PartyId = None
        self.progress: Progress = None
        self.profile: LinearAdditiveUtilitySpace = None
        self.domain: Domain = None
        self.reservation_bid: Bid = None

        self.last_received_bid: Bid = None
        self.all_bids: list[Bid] = []
        self.current_bid_index: int = -1

        self.getReporter().log(logging.INFO, "party is initialized")

    # Override
    def notifyChange(self, info: Inform):
        # A Settings message is the first message that will be sent to the agent
        # containing all the information about the negotiation session
        if isinstance(info, Settings):
            settings: Settings = cast(Settings, info)
            self.process_settings(settings, info)

        # A ActionDone message informs the agent of an action (an offer or an accept)
        # that is performed by any agent (including itself)
        elif isinstance(info, ActionDone):
            action: Action = cast(ActionDone, info).getAction()
            actor = action.getActor()

            # ignore action if it is our action
            if actor != self.me:
                # process action done by opponent
                self.process_opponent_action(action)

        # A YourTurn message notifies the agent that it is its turn to act
        elif isinstance(info, YourTurn):
            # execute a turn
            self.execute_turn()

        # A Finished message will be sent if the negotiation has ended (through agreement or deadline)
        elif isinstance(info, Finished):
            self.terminate()
        else:
            self.getReporter().log(logging.WARNING, "Ignoring unknown info " + str(info))

    # Override
    def getCapabilities(self):  # -> Capabilities
        return Capabilities(
            {"SAOP"}, {"geniusweb.profile.utilityspace.LinearAdditive"}
        )

    # Override
    def getDescription(self):
        return "Simple agent"

    # Override
    def terminate(self):
        self.getReporter().log(logging.INFO, "party is terminating")
        super().terminate()

    def process_settings(self, settings: Settings, info: Inform):
        self.me = settings.getID()
        # Progress towards the deadline
        self.progress = settings.getProgress()
        # The profile contains the preferences of the agent over the domain
        profile_connection = ProfileConnectionFactory.create(
            info.getProfile().getURI(), self.getReporter()
        )
        self.profile = profile_connection.getProfile()
        self.domain = self.profile.getDomain()
        self.reservation_bid = self.profile.getReservationBid()

        profile_connection.close()

    def process_opponent_action(self, action: Action):
        """
        Process an action that was received from the opponent.

        Args:
            action (Action): action of opponent
        """
        # If it is an offer, set the last received bid
        if isinstance(action, Offer):
            self.last_received_bid = cast(Offer, action).getBid()

    def execute_turn(self):
        # Determine next bid
        bid = self.find_bid()
        # Check if the last received offer is good enough compared to next bid
        if self.is_acceptable(self.last_received_bid, bid):
            # If so, accept the offer
            action = Accept(self.me, self.last_received_bid)
        else:
            # Otherwise, propose the next bid as a counter offer
            action = Offer(self.me, bid)

        # Send the chosen action
        self.send_action(action)

    def is_acceptable(self, received_bid: Bid, bid: Bid) -> bool:
        if received_bid is not None:
            # Check if the received bid has a better utility than the next bid (or equal utility)
            if self.profile.getUtility(received_bid) >= self.profile.getUtility(bid):
                self.getReporter().log(logging.INFO, "accept: the received bid has higher or equal utility to next bid")
                return True

            # Progress of the negotiation session between 0 and 1 (1 is deadline)
            progress = self.progress.get(time() * 1000)

            # Check if there is still time to receive a better offer
            if progress < 0.95:
                # If so, wait for better offer
                return False
            self.getReporter().log(logging.INFO, "reached timed-out condition")
            # Check if there is no reservation bid
            if self.reservation_bid is None:
                # If so, any agreement is better than no agreement
                self.getReporter().log(logging.INFO, "accept: there is no reservation bid")
                return True

            # Check if the received bid has at least the same utility as the reservation bid
            reserve_value = self.profile.getUtility(self.reservation_bid)
            if self.profile.getUtility(received_bid) >= reserve_value:
                self.getReporter().log(logging.INFO, "accept: the received bid has at least the same utility " +
                                                     "as the reservation bid of " + str(reserve_value))
                return True
        return False

    def find_bid(self) -> Bid:
        # Create a sorted list of bids
        # If it does not exist already
        if self.current_bid_index < 0:
            all_bids = AllBidsList(self.domain)
            self.getReporter().log(logging.INFO, "sorting all_bids list of size " + str(all_bids.size()))
            self.all_bids = sorted(all_bids, key=lambda x: self.profile.getUtility(x), reverse=True)
            self.current_bid_index = 0

        bid = self.all_bids[self.current_bid_index]
        self.current_bid_index += 1
        return bid

    def send_action(self, action: Action):
        """
        Sends an action to the opponent(s).

        Args:
            action (Action): action of this agent
        """
        self.getConnection().send(action)


class SimpleAgentA(SimpleAgent):
    def __init__(self):
        super().__init__()


class SimpleAgentB(SimpleAgent):
    def __init__(self):
        super().__init__()
