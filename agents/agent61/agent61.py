import logging
from random import randint
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
from geniusweb.progress.ProgressTime import ProgressTime
from geniusweb.references.Parameters import Parameters
from tudelft_utilities_logging.ReportToLogger import ReportToLogger

from .utils.opponent_model import OpponentModel


class Agent61(DefaultParty):
    """
    Agent61
    """

    def __init__(self):
        super().__init__()
        self.logger: ReportToLogger = self.getReporter()

        self.domain: Domain = None
        self.parameters: Parameters = None
        self.profile: LinearAdditiveUtilitySpace = None
        self.progress: ProgressTime = None
        self.me: PartyId = None
        self.other: str = None
        self.settings: Settings = None
        self.storage_dir: str = None

        self.reservation_bid: Bid = None
        self.last_received_bid: Bid = None
        self.opponent_model: OpponentModel = None
        self.logger.log(logging.INFO, "party is initialized")

        self.best_bids = None
        self.all_best_bids = None

    def notifyChange(self, data: Inform):
        """MUST BE IMPLEMENTED
        This is the entry point of all interaction with your agent after is has been initialised.
        How to handle the received data is based on its class type.

        Args:
            info (Inform): Contains either a request for action or information.
        """

        # a Settings message is the first message that will be send to your
        # agent containing all the information about the negotiation session.
        if isinstance(data, Settings):
            self.settings = cast(Settings, data)
            self.me = self.settings.getID()

            # progress towards the deadline has to be tracked manually through the use of the Progress object
            self.progress = self.settings.getProgress()

            self.parameters = self.settings.getParameters()
            self.storage_dir = self.parameters.get("storage_dir")

            # the profile contains the preferences of the agent over the domain
            profile_connection = ProfileConnectionFactory.create(
                data.getProfile().getURI(), self.getReporter()
            )
            self.profile = profile_connection.getProfile()
            self.domain = self.profile.getDomain()
            self.reservation_bid = self.profile.getReservationBid()
            profile_connection.close()

        # ActionDone informs you of an action (an offer or an accept)
        # that is performed by one of the agents (including yourself).
        elif isinstance(data, ActionDone):
            action = cast(ActionDone, data).getAction()
            actor = action.getActor()

            # ignore action if it is our action
            if actor != self.me:
                # obtain the name of the opponent, cutting of the position ID.
                self.other = str(actor).rsplit("_", 1)[0]

                # process action done by opponent
                self.opponent_action(action)
        # YourTurn notifies you that it is your turn to act
        elif isinstance(data, YourTurn):
            # execute a turn
            self.my_turn()

        # Finished will be send if the negotiation has ended (through agreement or deadline)
        elif isinstance(data, Finished):
            # terminate the agent MUST BE CALLED
            self.logger.log(logging.INFO, "party is terminating:")
            super().terminate()
        else:
            self.logger.log(logging.WARNING, "Ignoring unknown info " + str(data))

    def getCapabilities(self) -> Capabilities:
        """MUST BE IMPLEMENTED
        Method to indicate to the protocol what the capabilities of this agent are.
        Leave it as is for the ANL 2022 competition

        Returns:
            Capabilities: Capabilities representation class
        """
        return Capabilities(
            set(["SAOP"]),
            set(["geniusweb.profile.utilityspace.LinearAdditive"]),
        )

    def send_action(self, action: Action):
        """Sends an action to the opponent(s)

        Args:
            action (Action): action of this agent
        """
        self.getConnection().send(action)

    # give a description of your agent
    def getDescription(self) -> str:
        """MUST BE IMPLEMENTED
        Returns a description of your agent. 1 or 2 sentences.

        Returns:
            str: Agent description
        """
        return "Agent61 for CSE3210 (2022/23)."

    def opponent_action(self, action):
        """Process an action that was received from the opponent.

        Args:
            action (Action): action of opponent
        """
        # if it is an offer, set the last received bid
        if isinstance(action, Offer):
            # create opponent model if it was not yet initialised
            if self.opponent_model is None:
                self.opponent_model = OpponentModel(self.domain)

            bid = cast(Offer, action).getBid()

            # update opponent model with bid
            self.opponent_model.update(bid)
            # set bid as last received
            self.last_received_bid = bid

    def my_turn(self):
        """This method is called when it is our turn. It should decide upon an action
        to perform and send this action to the opponent.
        """
        bid = self.find_bid()
        # check if the last received offer is good enough
        if self.accept_condition(self.last_received_bid, bid):
            # if so, accept the offer
            action = Accept(self.me, self.last_received_bid)
        else:
            # if not, find a bid to propose as counter offer
            action = Offer(self.me, bid)

        # send the action
        self.send_action(action)

    def accept_condition(self, received_bid: Bid, next_bid: Bid) -> bool:
        if received_bid is None:
            return False

        received_value = self.profile.getUtility(received_bid)
        possible_value = self.profile.getUtility(next_bid)
        # progress of the negotiation session between 0 and 1 (1 is deadline)
        progress = self.progress.get(time() * 1000)
        x = 1 - (0.25 * progress)
        adjusted_value = x * float(possible_value)
        reserve_value = 0.5
        if self.reservation_bid is not None:
            reserve_value = self.profile.getUtility(self.reservation_bid)

        if received_value >= adjusted_value and received_value >= reserve_value:
            return True

        return False

    def find_bid(self) -> Bid:
        # compose a list of all possible bids
        alpha = 0.95
        eps = 0.001
        domain = self.profile.getDomain()
        all_bids = AllBidsList(domain)

        candidate_bids = self.get_bids(all_bids)
        best_bid = sorted(candidate_bids, key=lambda x: (self.score_bid(x, alpha, eps)), reverse=True)[0]
        if best_bid in self.best_bids:
            self.best_bids.remove(best_bid)

            if len(self.all_best_bids) > 1:
                self.best_bids.append(self.all_best_bids.pop(0))

        return best_bid

    def get_bids(self, all_bids):
        if self.best_bids is None:
            split_off = max(int(all_bids.size() / 100), 400)
            self.all_best_bids = sorted(all_bids, key=lambda x: self.profile.getUtility(x), reverse=True)
            self.best_bids = self.all_best_bids[:split_off]
            self.all_best_bids = self.all_best_bids[split_off:]

        random_bids = []

        # take 500 attempts to find a bid according to a heuristic score

        for _ in range(max(len(self.best_bids), 100)):
            random_bids.append(all_bids.get(randint(0, all_bids.size() - 1)))

        return self.best_bids + random_bids

    def score_bid(self, bid: Bid, alpha: float = 0.95, eps: float = 0.1) -> float:
        """Calculate heuristic score for a bid

        Args:
            bid (Bid): Bid to score
            alpha (float, optional): Trade-off factor between self interested and
                altruistic behaviour. Defaults to 0.95.
            eps (float, optional): Time pressure factor, balances between conceding
                and Boulware behaviour over time. Defaults to 0.1.

        Returns:
            float: score
        """
        progress = self.progress.get(time() * 1000)

        our_utility = float(self.profile.getUtility(bid))

        time_pressure = 1.0 - progress ** (1 / eps)
        score = alpha * time_pressure * our_utility

        if self.opponent_model is not None:
            opponent_utility = self.opponent_model.get_predicted_utility(bid)
            opponent_score = (1.0 - alpha * time_pressure) * opponent_utility
            score += opponent_score

        return score
