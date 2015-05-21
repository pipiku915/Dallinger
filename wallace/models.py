"""Define Wallace's core models."""

from uuid import uuid4
from datetime import datetime

from .db import Base

from sqlalchemy import ForeignKey, or_, and_
from sqlalchemy import Column, String, Text, Enum, Integer, Boolean
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.associationproxy import association_proxy

import inspect

DATETIME_FMT = "%Y-%m-%dT%H:%M:%S.%f"


def new_uuid():
    """Generate a unique identifier."""
    return uuid4().hex


def timenow():
    """A string representing the current date and time."""
    time = datetime.now()
    return time.strftime(DATETIME_FMT)


class Network(Base):

    """A collection of Nodes and Vectors."""

    __tablename__ = "network"

    # the unique network id
    uuid = Column(String(32), primary_key=True, default=new_uuid)

    # the network type -- this allows for inheritance
    type = Column(String(50))
    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'base'
    }

    # the time when the node was created
    creation_time = Column(String(26), nullable=False, default=timenow)

    # how big the network can get, this number is used by the full()
    # method to decide whether the network is full
    max_size = Column(Integer, nullable=False, default=1e6)

    # whether the network is currently full
    full = Column(Boolean, nullable=False, default=False)

    # the role of the network, by default wallace initializes all
    # networks as either "practice" or "experiment"
    role = Column(String(26), nullable=False, default="default")

    # unused by default, these columns store additional properties used
    # by other types of network
    property1 = Column(String(26), nullable=True, default=None)
    property2 = Column(String(26), nullable=True, default=None)
    property3 = Column(String(26), nullable=True, default=None)
    property4 = Column(String(26), nullable=True, default=None)
    property5 = Column(String(26), nullable=True, default=None)

    def __len__(self):
        """The size of a network is undefined.

        The length of a network is confusing because it might refer either
        to the number of agents, sources, or nodes. Better to be explicit.
        """
        raise SyntaxError(
            "len is not defined for networks. " +
            "Use len(net.nodes()) instead.")

    def __repr__(self):
        """The string representation of a network."""
        return "<Network-{}-{} with {} nodes, {} vectors, {} infos, {} transmissions and {} transformations>".format(
            self.uuid[:6],
            self.type,
            len(self.nodes()),
            len(self.vectors()),
            len(self.infos()),
            len(self.transmissions()),
            len(self.transformations()))

    """ ###################################
    Methods that get things about a Network
    ################################### """

    def nodes(self, type=None, status="alive", participant_uuid=None):
        """
        Get nodes in the network.

        type specifies the type of Node. Status can be "all", "alive"
        (default), "dead" or "failed". If a participant_uuid is passed only
        nodes with that participant_uuid will be returned.
        """
        if type is None:
            type = Node

        if not issubclass(type, Node):
            raise(TypeError("{} is not a valid node type.".format(type)))

        if status not in ["all", "alive", "dead", "failed"]:
            raise ValueError("{} is not a valid node status".format(status))

        if participant_uuid is not None:
            if status == "all":
                return type\
                    .query\
                    .filter_by(network_uuid=self.uuid, participant_uuid=participant_uuid)\
                    .order_by(type.creation_time)\
                    .all()
            else:
                return type\
                    .query\
                    .filter_by(network_uuid=self.uuid, participant_uuid=participant_uuid, status=status)\
                    .order_by(type.creation_time)\
                    .all()
        else:
            if status == "all":
                return type\
                    .query\
                    .filter_by(network_uuid=self.uuid)\
                    .order_by(type.creation_time)\
                    .all()
            else:
                return type\
                    .query\
                    .filter_by(status=status, network_uuid=self.uuid)\
                    .order_by(type.creation_time)\
                    .all()

    def infos(self, type=None, origin_status="alive"):
        """
        Get infos in the network.

        type specifies the type of info (defaults to Info). only infos created
        by nodes with a status of origin_status will be returned. origin_status
        can be "all", "alive" (default), "dead" or "failed". To get infos from
        a specific node, see the infos() method in class Node.
        """
        if type is None:
            type = Info
        if origin_status not in ["all", "alive", "dead", "failed"]:
            raise ValueError("{} is not a valid origin status".format(origin_status))

        if origin_status == "all":
            return Info.query\
                .filter(network_uuid=self.uuid)\
                .order_by(Info.creation_time).all()
        else:
            return Info.query.join(Info.origin)\
                .filter(and_(Info.network_uuid == self.uuid, Node.status == origin_status))\
                .order_by(Info.creation_time).all()

    def transmissions(self, status="all", vector_status="alive"):
        """
        Get transmissions in the network.

        Only transmissions along vectors with a status of vector_status will
        be returned. vector_status "all", "alive" (default), "dead", or
        "failed". To get transmissions from a specific vector, see the
        transmissions() method in class Vector.
        """
        if status not in ["all", "pending", "received"]:
            raise(ValueError("You cannot get transmission of status {}.".format(status) +
                  "Status can only be pending, received or all"))
        if vector_status not in ["all", "alive", "dead", "failed"]:
            raise ValueError("{} is not a valid vector status".format(vector_status))

        if status == "all":
            if vector_status == "all":
                return Transmission.query\
                    .filter_by(network_uuid=self.uuid)\
                    .order_by(Transmission.transmit_time).all()
            else:
                return Transmission.query.join(Transmission.vector)\
                    .filter(and_(Transmission.network_uuid == self.uuid, Vector.status == vector_status))\
                    .order_by(Transmission.transmit_time).all()
        else:
            if vector_status == "all":
                return Transmission.query\
                    .filter(and_(Transmission.network_uuid == self.uuid, Transmission.status == status))\
                    .order_by(Transmission.transmit_time).all()
            else:
                return Transmission.query.join(Transmission.vector)\
                    .filter(and_(Transmission.network_uuid == self.uuid, Transmission.status == status, Vector.status == vector_status))\
                    .order_by(Transmission.transmit_time).all()

    def transformations(self, type=None, node_status="alive"):
        """
        Get transformations in the network.

        type specifies the type of transformation (defaults to Transformation).
        only transformations at nodes with a status of node_status will be returned.
        node_status can be "all", "alive" (default), "dead" or "failed".
        To get transformations from a specific node see the transformations() method in class Node.
        """
        if type is None:
            type = Transformation

        if node_status not in ["all", "alive", "dead", "failed"]:
            raise ValueError("{} is not a valid origin status".format(node_status))

        if node_status == "all":
            return Transformation.query\
                .filter_by(network_uuid=self.uuid)\
                .order_by(Transformation.transform_time).all()
        else:
            return Transformation.query.join(Transformation.node)\
                .filter(and_(Transformation.network_uuid == self.uuid, Node.status == node_status))\
                .order_by(Transformation.transform_time).all()

    def latest_transmission_recipient(self, status="alive"):
        """
        Get the node of the given status that most recently received a transmission.

        Status can be "all", "alive" (default), "dead" or "failed".
        """
        received_transmissions = reversed(self.transmissions(status="received"))

        return next(
            (t.destination for t in received_transmissions
                if (t.destination.status == status)),
            None)

    def vectors(self, status="alive"):
        """
        Get vectors in the network.

        Status can be "all", "alive" (default), "dead" or "failed". To get the
        vectors attached to a specific node, see Node.vectors().
        """
        if status not in ["all", "alive", "dead", "failed"]:
            raise ValueError("{} is not a valid vector status".format(status))

        if status == "all":
            return Vector.query\
                .filter_by(network_uuid=self.uuid)\
                .all()
        else:
            return Vector.query\
                .filter_by(network_uuid=self.uuid)\
                .filter_by(status=status)\
                .all()

    """ ###################################
    Methods that make Networks do things
    ################################### """

    def add(self, base):
        """
        Add a node to the network.

        Only Nodes can be added to a network.
        """
        if isinstance(base, list):
            for b in base:
                self.add(b)
        elif isinstance(base, Node):
            base.network = self
            self.calculate_full()
        else:
            raise(TypeError("Cannot add {} to the network as it is a {}. " +
                            "Only Nodes can be added to networks.").format(base, type(base)))

    def calculate_full(self):
        """Set whether the network is full."""
        num_alive = len(self.nodes(status="alive"))
        num_dead = len(self.nodes(status="dead"))
        self.full = (num_alive + num_dead) >= self.max_size

    def print_verbose(self):
        """Print a verbose representation of a network."""
        print "Nodes: "
        for a in (self.nodes(status="dead") +
                  self.nodes(status="alive")):
            print a

        print "\nVectors: "
        for v in (self.vectors(status="dead") +
                  self.vectors(status="alive")):
            print v

        print "\nInfos: "
        for i in (self.infos(origin_status="dead") +
                  self.infos(origin_status="alive")):
            print i

        print "\nTransmissions: "
        for t in (self.transmissions(vector_status="dead") +
                  self.transmissions(vector_status="alive")):
            print t

        print "\nTransformations: "
        for t in (self.transformations(node_status="dead") +
                  self.transformations(node_status="alive")):
            print t


class Node(Base):

    """A point in a network."""

    __tablename__ = "node"

    # the unique node id
    uuid = Column(String(32), primary_key=True, default=new_uuid)

    # the node type -- this allows for inheritance
    type = Column(String(50))
    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'base'
    }

    # the network that this node is a part of
    network_uuid = Column(String(32), ForeignKey('network.uuid'))
    network = relationship(Network, backref="all_nodes")

    # the time when the node was created
    creation_time = Column(String(26), nullable=False, default=timenow)

    # the status of the node
    status = Column(Enum("alive", "dead", "failed", name="node_status"),
                    nullable=False, default="alive")

    # the time when the node changed from alive->dead or alive->failed
    time_of_death = Column(String(26), default=None)

    # the participant uuid is the sha512 hash of the psiTurk uniqueId of the
    # participant who was this node.
    participant_uuid = Column(String(128), default=None)

    # unused by default, these columns store additional properties used
    # by other types of node
    property1 = Column(String(26), default=None)
    property2 = Column(String(26), default=None)
    property3 = Column(String(26), default=None)
    property4 = Column(String(26), default=None)
    property5 = Column(String(26), default=None)

    def __repr__(self):
        """The string representation of a node."""
        return "Node-{}-{}".format(self.uuid[:6], self.type)

    """ ###################################
    Methods that get things about a node
    ################################### """

    def vectors(self, direction="all", status="alive"):
        """
        Get vectors that connect at this node.

        Direction can be "incoming", "outgoing" or "all" (default).
        Status can be "all", "alive" (default), "dead", "failed".
        """
        if direction not in ["all", "incoming", "outgoing"]:
            raise ValueError(
                "{} is not a valid vector direction. "
                "Must be all, incoming or outgoing.".format(direction))
        if status not in ["all", "alive", "dead", "failed"]:
            raise ValueError("{} is not a valid vector status".format(status))

        if direction == "all":

            if status == "all":
                return Vector.query\
                    .filter(or_(Vector.destination_uuid == self.uuid, Vector.origin_uuid == self.uuid))\
                    .all()
            else:
                return Vector.query\
                    .filter(and_(Vector.status == status, or_(Vector.destination_uuid == self.uuid, Vector.origin_uuid == self.uuid)))\
                    .all()

        if direction == "incoming":

            if status == "all":
                return Vector.query\
                    .filter_by(destination_uuid=self.uuid)\
                    .all()
            else:
                return Vector.query\
                    .filter_by(destination_uuid=self.uuid, status=status)\
                    .all()

        if direction == "outgoing":

            if status == "all":
                return Vector.query\
                    .filter_by(origin_uuid=self.uuid)\
                    .all()
            else:
                return Vector.query\
                    .filter_by(origin_uuid=self.uuid, status=status)\
                    .all()

    def neighbors(self, type=None, status="alive", connection="to"):
        """
        Get a node's neighbors.

        Type must be a subclass of Node (default is Node).
        Status can be "alive" (default), "dead", "failed" or "all".
        Connection can be "to" (default), "from", "either", or "both".
        """
        if type is None:
            type = Node

        if not issubclass(type, Node):
            raise ValueError("{} is not a valid neighbor type, needs to be a subclass of Node.".format(type))

        if status not in ["alive", "dead", "failed", "all"]:
            raise ValueError("{} is not a valid neighbor status".format(status))

        if connection not in ["both", "either", "from", "to"]:
            raise ValueError("{} not a valid neighbor connection. Should be all, to or from.".format(connection))

        if connection == "to":
            return [v.destination for v in self.vectors(direction="outgoing", status=status) if isinstance(v.destination, type) and v.destination.status == status]

        if connection == "from":
            return [v.origin for v in self.vectors(direction="incoming", status=status) if isinstance(v.origin, type) and v.origin.status == status]

        if connection == "either":
            neighbors = list(set(
                [v.destination for v in self.vectors(direction="outgoing", status=status)
                    if isinstance(v.destination, type) and v.destination.status == status] +
                [v.origin for v in self.vectors(direction="incoming", status=status)
                    if isinstance(v.origin, type) and v.origin.status == status]))
            return neighbors.sort(key=lambda node: node.creation_time)

        if connection == "both":
            return [node for node in
                    [v.destination for v in self.vectors(direction="outgoing", status=status)
                        if isinstance(v.destination, type) and v.destination.status == status]
                    if node in
                    [v.origin for v in self.vectors(direction="incoming", status=status)
                        if isinstance(v.origin, type) and v.origin.status == status]]

    def is_connected(self, other_node, direction="to", status="alive"):
        """
        Check whether this node is connected to the other_node.

        other_node can be a list of nodes or a single node.
        direction can be "to" (default), "from", "both" or "either".
        status can be "alive" (default), "dead", "failed" and "all".
        """

        other_node = self.flatten([other_node])

        for node in other_node:
            if not isinstance(node, Node):
                raise(TypeError("is_connected cannot parse objects of type {}.".
                      format([type(node) for node in other_node if not isinstance(node, Node)][0])))

        if status not in ["alive", "dead", "failed", "all"]:
            raise ValueError("{} is not a valid connection status".format(status))

        if direction not in ["to", "from", "either", "both"]:
            raise ValueError("{} is not a valid direction for is_connected".format(direction))

        if direction == "to":
            all_relevant_vectors = Vector.query.with_entities(Vector.destination_uuid)\
                .filter_by(origin_uuid=self.uuid).all()
            for i, n in enumerate(other_node):
                other_node[i] = any([v for v in all_relevant_vectors if v.destination_uuid == n.uuid])
        elif direction == "from":
            all_relevant_vectors = Vector.query.with_entities(Vector.origin_uuid)\
                .filter_by(destination_uuid=self.uuid).all()
            for i, n in enumerate(other_node):
                other_node[i] = any([v for v in all_relevant_vectors if v.origin_uuid == n.uuid])
        elif direction == "either":
            all_relevant_vectors = Vector.query.with_entities(Vector.destination_uuid, Vector.origin_uuid)\
                .filter(or_(Vector.destination_uuid == self.uuid, Vector.origin_uuid == self.uuid)).all()
            for i, n in enumerate(other_node):
                other_node[i] = (any([v for v in all_relevant_vectors if v.origin_uuid == n.uuid]) or
                                 any([v for v in all_relevant_vectors if v.origin_uuid == n.uuid]))
        elif direction == "both":
            all_relevant_vectors = Vector.query.with_entities(Vector.destination_uuid, Vector.origin_uuid)\
                .filter(or_(Vector.destination_uuid == self.uuid, Vector.origin_uuid == self.uuid)).all()
            for i, n in enumerate(other_node):
                other_node[i] = (any([v for v in all_relevant_vectors if v.origin_uuid == n.uuid]) and
                                 any([v for v in all_relevant_vectors if v.origin_uuid == n.uuid]))
        if len(other_node) == 1:
            return other_node[0]
        else:
            return other_node

    def infos(self, type=None):
        """
        Get infos that originate from this node.
        Type must be a subclass of info, the default is Info.
        """
        if type is None:
            type = Info

        if not issubclass(type, Info):
            raise(TypeError("Cannot get-info of type {} as it is not a valid type.".format(type)))

        return type\
            .query\
            .filter_by(origin_uuid=self.uuid)\
            .all()

    def transmissions(self, direction="outgoing", status="all"):
        """
        Get transmissions sent to or from this node.

        Direction can be "all", "incoming" or "outgoing" (default).
        Status can be "all" (default), "pending", or "received".
        """
        if direction not in ["incoming", "outgoing", "all"]:
            raise(ValueError("You cannot get transmissions of direction {}.".format(direction) +
                  "Type can only be incoming, outgoing or all."))

        if status not in ["all", "pending", "received"]:
            raise(ValueError("You cannot get transmission of status {}.".format(status) +
                  "Status can only be pending, received or all"))

        if direction == "all":
            if status == "all":
                return Transmission.query.filter(or_(Transmission.destination_uuid == self.uuid, Transmission.origin_uuid == self.uuid)).all()
            else:
                return Transmission.query.filter(and_(Transmission.status == status, or_(Transmission.destination_uuid == self.uuid, Transmission.origin_uuid == self.uuid))).all()
        if direction == "incoming":
            if status == "all":
                return Transmission.query.filter_by(destination_uuid=self.uuid).all()
            else:
                return Transmission.query.filter(and_(Transmission.destination_uuid == self.uuid, Transmission.status == status)).all()
        if direction == "outgoing":
            if status == "all":
                return Transmission.query.filter_by(origin_uuid=self.uuid).all()
            else:
                return Transmission.query.filter(and_(Transmission.origin_uuid == self.uuid, Transmission.status == status)).all()

    def transformations(self, type=None):
        """
        Get Transformations done by this Node.

        type must be a type of Transformation (defaults to Transformation)
        """
        if type is None:
            type = Transformation
        return type\
            .query\
            .filter_by(node_uuid=self.uuid)\
            .all()

    """ ###################################
    Methods that make nodes do things
    ################################### """

    def die(self):
        """
        Kill a node.

        Set the node's status to "dead". Also kills all vectors that connect
        to or from the node. You cannot kill a node that is already dead or
        failed.
        """
        if self.status != "alive":
            raise AttributeError("You cannot kill {} - it is already {}.".format(self, self.status))

        else:
            self.status = "dead"
            self.time_of_death = timenow()
            for v in self.vectors(status="alive"):
                v.die()

    def fail(self):
        """
        Fail a node, setting its status to "failed".

        Also fails all vectors that connect to or from the node.
        You cannot fail a node that has already failed, but you
        can fail a dead node.
        """
        if self.status == "failed":
            raise AttributeError("Cannot fail {} - it has already failed.".format(self))

        else:
            self.status = "failed"
            self.time_of_death = timenow()

            for v in (self.vectors(status="dead") +
                      self.vectors(status="alive")):
                v.fail()

    def connect(self, other_node, direction="to"):
        from wallace.nodes import Source
        """Create a vector from self to other_node.

        other_node may be a (nested) list of nodes.
        Will raise an error if:
            (1) other_node is not a node or list of nodes
            (2) other_node is a source
            (3) other_node is not alive
            (4) other_node is yourself
            (5) other_node is in a different network
        If self is already connected to other_node a Warning
        is raised and nothing happens.
        """

        if direction not in ["to", "from", "both"]:
            raise ValueError("{} is not a valid direction for connect()".format(direction))

        other_node = self.flatten([other_node])

        if self in other_node:
            raise ValueError("A node cannot connect to itself.")

        for node in other_node:
            if not isinstance(node, Node):
                raise(TypeError("connect_to cannot parse a list containing objects of type {}.".
                                format([type(node) for node in other_node if not isinstance(node, Node)][0])))

        to_nodes = other_node
        from_nodes = other_node
        if direction == "to":
            from_nodes = []
        if direction == "from":
            to_nodes = []

        if to_nodes:
            already_connected_to = self.is_connected(direction="to", other_node=to_nodes)
            if (not isinstance(already_connected_to, list)):
                already_connected_to = [already_connected_to]
            if any(already_connected_to):
                #raise Warning("Warning! {} instructed to connect to nodes it already has a connection to, instruction will be ignored.".format(self))
                print("Warning! {} instructed to connect to nodes it already has a connection to, instruction will be ignored.".format(self))
                to_nodes = [node for node, connected in zip(to_nodes, already_connected_to) if not connected]

        if from_nodes:
            already_connected_from = self.is_connected(direction="from", other_node=from_nodes)
            if (not isinstance(already_connected_from, list)):
                already_connected_from = [already_connected_from]
            if any(already_connected_from):
                raise Warning("Warning! {} instructed to connect from nodes it already has a connection from, instruction will be ignored.".format(self))
                from_nodes = [node for node, connected in zip(from_nodes, already_connected_from) if not connected]

        for node in to_nodes:
            if isinstance(node, Source):
                raise(TypeError("{} cannot connect_to {} as it is a Source.".format(self, node)))
            if node.status != "alive":
                raise(ValueError("{} cannot connect to {} as it is {}".format(self, node, node.status)))
            if self.network_uuid != node.network_uuid:
                raise(ValueError(("{} cannot connect to {} as they are not " +
                                  "in the same network. {} is in network {}, " +
                                  "but {} is in network {}.")
                                 .format(self, node, self, self.network_uuid,
                                         node, node.network_uuid)))
            Vector(origin=self, destination=node)

        for node in from_nodes:
            if node.status != "alive":
                raise(ValueError("{} cannot connect from {} as it is {}".format(self, node, node.status)))
            if self.network_uuid != node.network_uuid:
                raise(ValueError(("{} cannot connect from {} as they are not " +
                                  "in the same network. {} is in network {}, " +
                                  "but {} is in network {}.")
                                 .format(self, node, self, self.network_uuid,
                                         node, node.network_uuid)))
            Vector(origin=node, destination=self)

    def connect_from(self, other_node):
        """Create a vector from other_node to self.

        other_node may be a list of nodes
        see Node.connect_to()
        """
        self.connect(other_node=other_node, direction="from")

    def connect_to(self, other_node):
        self.connect(other_node=other_node, direction="to")

    def flatten(self, l):
        if l == []:
            return l
        if isinstance(l[0], list):
            return self.flatten(l[0]) + self.flatten(l[1:])
        return l[:1] + self.flatten(l[1:])

    def transmit(self, what=None, to_whom=None):
        """
        Transmit one or more infos from one node to another.

        "what" dictates which infos are sent, it can be:
            (1) None (in which case the node's _what method is called).
            (2) an Info (in which case the node transmits the info)
            (3) a subclass of Info (in which case the node transmits all its infos of that type)
            (4) a list of any combination of the above
        "to_whom" dictates which node(s) the infos are sent to, it can be:
            (1) None (in which case the node's _to_whom method is called)
            (2) a Node (in which case the node transmits to that node)
            (3) a subclass of Node (in which case the node transmits to all nodes of that type it is connected to)
            (4) a list of any combination of the above
        Will additionally raise an error if:
            (1) _what() or _to_whom() returns None or a list containing None.
            (2) what is/contains an info that does not originate from the transmitting node
            (3) to_whom is/contains a node that the transmitting node does have have a live connection with.
        """
        # make the list of what
        what = self.flatten([what])
        for i in range(len(what)):
            if what[i] is None:
                what[i] = self._what()
            elif inspect.isclass(what[i]) and issubclass(what[i], Info):
                what[i] = self.infos(type=what[i])
        what = self.flatten(what)
        for i in range(len(what)):
            if isinstance(what[i], Info):
                pass
            elif what[i] is None:
                raise ValueError("The _what() of {} is returning None: {}.".format(self, self._what()))
            elif inspect.isclass(what[i]) and issubclass(what[i], Info):
                what[i] = self.infos(type=what[i])
            else:
                raise ValueError("Cannot transmit {}".format(what[i]))
        what = set(self.flatten(what))

        # make the list of to_whom
        to_whom = self.flatten([to_whom])
        for i in range(len(to_whom)):
            if to_whom[i] is None:
                to_whom[i] = self._to_whom()
            elif inspect.isclass(to_whom[i]) and issubclass(to_whom[i], Node):
                to_whom[i] = self.neighbors(connection="to", type=to_whom[i])
        to_whom = self.flatten(to_whom)
        for i in range(len(to_whom)):
            if isinstance(to_whom[i], Node):
                pass
            elif to_whom[i] is None:
                raise ValueError("The _to_whom() of {} is returning None: {}.".format(self, self._to_whom()))
            elif inspect.isclass(to_whom[i]) and issubclass(to_whom[i], Node):
                to_whom[i] = self.neighbors(connection="to", type=to_whom[i])
            else:
                raise ValueError("Cannot transmit to {}".format(to_whom[i]))
        to_whom = set(self.flatten(to_whom))

        for w in what:
            if w.origin_uuid != self.uuid:
                raise ValueError("{} cannot transmit {} as it is not its origin".format(self, w))
            for tw in to_whom:
                if not self.is_connected(other_node=tw):
                    raise ValueError("{} cannot transmit to {} as it does not have a connection to them".format(self, to_whom))
                vector = [v for v in self.vectors(direction="outgoing") if v.destination_uuid == tw.uuid][0]
                Transmission(info=w, vector=vector)

    def _what(self):
        return Info

    def _to_whom(self):
        return Node

    def receive(self, what=None):
        """
        Mark transmissions as received, then pass their infos to update().

        "what" can be:
            (1) "all" (the default) in which case all pending transmissions are received
            (2) a specific transmission.
        Will raise an error if the node is told to receive a transmission it has not been sent.
        """
        received_transmissions = []
        if what is None:
            pending_transmissions = self.transmissions(direction="incoming", status="pending")
            for transmission in pending_transmissions:
                transmission.status = "received"
                transmission.receive_time = timenow()
                received_transmissions.append(transmission)

        elif isinstance(what, Transmission):
            if what in self.transmissions(direction="incoming", status="pending"):
                transmission.status = "received"
                what.receive_time = timenow()
                received_transmissions.append(what)
            else:
                raise(ValueError("{} cannot receive {} as it is not in its pending_transmissions".format(self, what)))
        else:
            raise ValueError("Nodes cannot receive {}".format(what))

        self.update([t.info for t in received_transmissions])

    def update(self, infos):
        """
        Update controls the default behavior of a node when it receives infos.
        By default it does nothing.
        """
        pass

    def replicate(self, info_in):
        from transformations import Replication
        info_out = type(info_in)(origin=self, contents=info_in.contents)
        Replication(info_in=info_in, info_out=info_out)

    def mutate(self, info_in):
        from transformations import Mutation
        info_out = type(info_in)(origin=self, contents=info_in._mutated_contents())
        Mutation(info_in=info_in, info_out=info_out)


class Vector(Base):

    """
    A Vector is a path that links two Nodes.
    Nodes can only send each other information if they are linked by a Vector.
    """

    """ ###################################
    SQLAlchemy stuff. Touch at your peril!
    ################################### """

    __tablename__ = "vector"

    # the unique vector id
    uuid = Column(String(32), primary_key=True, default=new_uuid)

    # the origin node
    origin_uuid = Column(String(32), ForeignKey('node.uuid'))
    origin = relationship(Node, foreign_keys=[origin_uuid],
                          backref="all_outgoing_vectors")

    # the destination node
    destination_uuid = Column(String(32), ForeignKey('node.uuid'))
    destination = relationship(Node, foreign_keys=[destination_uuid],
                               backref="all_incoming_vectors")

    # the network that this vector is in
    network_uuid = Column(String(32), ForeignKey('network.uuid'))
    network = relationship(Network, backref="all_vectors")

    # the time when the node was created
    creation_time = Column(String(26), nullable=False, default=timenow)

    # the status of the vector
    status = Column(Enum("alive", "dead", "failed", name="vector_status"),
                    nullable=False, default="alive")

    # the time when the vector changed from alive->dead
    time_of_death = Column(String(26), default=None)

    # unused by default, these columns store additional properties used
    # by other types of vector
    property1 = Column(String(26), default=None)
    property2 = Column(String(26), default=None)
    property3 = Column(String(26), default=None)
    property4 = Column(String(26), default=None)
    property5 = Column(String(26), default=None)

    def __init__(self, origin, destination):
        #super(Vector, self).__init__()
        self.origin = origin
        self.origin_uuid = origin.uuid
        self.destination = destination
        self.destination_uuid = destination.uuid
        self.network = origin.network
        self.network_uuid = origin.network_uuid

    def __repr__(self):
        """The string representation of a vector."""
        return "Vector-{}-{}".format(
            self.origin_uuid[:6], self.destination_uuid[:6])

    ###################################
    # Methods that get things about a Vector
    ###################################

    def transmissions(self, status="all"):
        """
        Get transmissions sent along this Vector.
        Status can be "all" (the default), "pending", or "received".
        """

        if status not in ["all", "pending", "received"]:
            raise(ValueError("You cannot get {} transmissions.".format(status) +
                  "Status can only be pending, received or all"))

        if status == "all":
            return Transmission\
                .query\
                .filter_by(vector_uuid=self.uuid)\
                .all()
        else:
            return Transmission\
                .query\
                .filter_by(vector_uuid=self.uuid, status=status)\
                .all()

    ###################################
    # Methods that make Vectors do things
    ###################################

    def die(self):
        if self.status != "alive":
            raise AttributeError("You cannot kill {}, it is {}.".format(self, self.status))
        else:
            self.status = "dead"
            self.time_of_death = timenow()

    def fail(self):
        if self.status == "failed":
            raise AttributeError("You cannot fail {}, it has already failed".format(self))
        else:
            self.status = "failed"
            self.time_of_death = timenow()


class Info(Base):

    """A unit of information sent along a vector via a transmission."""

    __tablename__ = "info"

    # the unique info id
    uuid = Column(String(32), primary_key=True, default=new_uuid)

    # the info type -- this allows for inheritance
    type = Column(String(50))
    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'base'
    }

    # the node that created this info
    origin_uuid = Column(String(32), ForeignKey('node.uuid'))
    origin = relationship(Node, backref='all_infos')

    # the network the info is in
    network_uuid = Column(String(32), ForeignKey('network.uuid'))
    network = relationship(Network, backref="all_infos")

    # the time when the info was created
    creation_time = Column(String(26), nullable=False, default=timenow)

    # the contents of the info
    contents = Column(Text(), default=None)

    # unused by default, these columns store additional properties used
    # by other types of info
    property1 = Column(String(26), default=None)
    property2 = Column(String(26), default=None)
    property3 = Column(String(26), default=None)
    property4 = Column(String(26), default=None)
    property5 = Column(String(26), default=None)

    def __init__(self, origin, contents=None):
        self.origin = origin
        self.origin_uuid = origin.uuid
        self.contents = contents
        self.network_uuid = origin.network_uuid
        self.network = origin.network

    @validates("contents")
    def _write_once(self, key, value):
        existing = getattr(self, key)
        if existing is not None:
            raise ValueError("The contents of an info is write-once.")
        return value

    def __repr__(self):
        """The string representation of an info."""
        return "Info-{}-{}".format(self.uuid[:6], self.type)

    def transmissions(self, status="all"):
        if status not in ["all", "pending", "received"]:
            raise(ValueError("You cannot get transmission of status {}.".format(status) +
                             "Status can only be pending, received or all"))
        if status == "all":
            return Transmission\
                .query\
                .filter_by(info_uuid=self.uuid)\
                .all()
        else:
            return Transmission\
                .query\
                .filter(and_(Transmission.info_uuid == self.uuid, Transmission.status == status))\
                .all()

    def transformations(self, relationship="all"):
        if relationship not in ["all", "parent", "child"]:
            raise(ValueError("You cannot get transformations of relationship {}".format(relationship) +
                  "Relationship can only be parent, child or all."))

        if relationship == "all":
            return Transformation\
                .query\
                .filter(or_(Transformation.info_in == self, Transformation.info_out == self))\
                .all()

        if relationship == "parent":
            return Transformation\
                .query\
                .filter_by(info_in=self)\
                .all()

        if relationship == "child":
            return Transformation\
                .query\
                .filter_by(info_out=self)\
                .all()

    def _mutated_contents(self):
        raise NotImplementedError("_mutated_contents needs to be overwritten in class {}".format(type(self)))


class Transmission(Base):
    """
    A Transmission is when an Info is sent along a Vector.
    """

    __tablename__ = "transmission"

    # the unique transmission id
    uuid = Column(String(32), primary_key=True, default=new_uuid)

    # the vector the transmission passed along
    vector_uuid = Column(String(32), ForeignKey('vector.uuid'))
    vector = relationship(Vector, backref='all_transmissions')

    # the info that was transmitted
    info_uuid = Column(String(32), ForeignKey('info.uuid'))
    info = relationship(Info, backref='all_transmissions')

    # the origin node
    origin_uuid = Column(String(32), ForeignKey('node.uuid'))
    origin = relationship(Node, foreign_keys=[origin_uuid],
                          backref="all_outgoing_transmissions")

    # the destination node
    destination_uuid = Column(String(32), ForeignKey('node.uuid'))
    destination = relationship(Node, foreign_keys=[destination_uuid],
                               backref="all_incoming_transmissions")

    # the network of the transformation
    network_uuid = Column(String(32), ForeignKey('network.uuid'))
    network = relationship(Network, backref="networks_transmissions")

    # the time at which the transmission occurred
    transmit_time = Column(String(26), nullable=False, default=timenow)

    # the time at which the transmission was received
    receive_time = Column(String(26), default=None)

    # the status of the transmission, can be pending or received
    status = Column(Enum("pending", "received", name="transmission_status"),
                    nullable=False, default="pending")

    # unused by default, these columns store additional properties used
    # by other types of transmission
    property1 = Column(String(26), default=None)
    property2 = Column(String(26), default=None)
    property3 = Column(String(26), default=None)
    property4 = Column(String(26), default=None)
    property5 = Column(String(26), default=None)

    def __init__(self, vector, info):
        #super(Transmission, self).__init__()
        self.vector_uuid = vector.uuid
        self.vector = vector
        self.info_uuid = info
        self.info = info
        self.origin_uuid = vector.origin_uuid
        self.origin = vector.origin
        self.destination_uuid = vector.destination_uuid
        self.destination = vector.destination
        self.network_uuid = vector.network_uuid
        self.network = vector.network

    def mark_received(self):
        self.receive_time = timenow()
        self.status = "received"

    def __repr__(self):
        """The string representation of a transmission."""
        return "Transmission-{}".format(self.uuid[:6])


class Transformation(Base):
    """
    A Transformation is when one info is used to generate another Info.
    """

    __tablename__ = "transformation"

    # the transformation type -- this allows for inheritance
    type = Column(String(50))
    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'base'
    }

    # the unique transformation id
    uuid = Column(String(32), primary_key=True, default=new_uuid)

    # the info before it was transformed
    info_in_uuid = Column(String(32), ForeignKey('info.uuid'))
    info_in = relationship(Info, foreign_keys=[info_in_uuid],
                           backref="transformation_applied_to")

    # the info produced as a result of the transformation
    info_out_uuid = Column(String(32), ForeignKey('info.uuid'))
    info_out = relationship(Info, foreign_keys=[info_out_uuid],
                            backref="transformation_whence")

    node_uuid = Column(String(32), ForeignKey('node.uuid'))
    node = relationship(Node, backref='transformations_here')

    # the network of the transformation
    network_uuid = Column(String(32), ForeignKey('network.uuid'))
    network = relationship(Network, backref="networks_transformations")

    # the time at which the transformation occurred
    transform_time = Column(String(26), nullable=False, default=timenow)

    # unused by default, these columns store additional properties used
    # by other types of transformation
    property1 = Column(String(26), default=None)
    property2 = Column(String(26), default=None)
    property3 = Column(String(26), default=None)
    property4 = Column(String(26), default=None)
    property5 = Column(String(26), default=None)

    def __repr__(self):
        """The string representation of a transformation."""
        return "Transformation-{}".format(self.uuid[:6])

    def __init__(self, info_in, info_out=None):
        self.check_for_transformation(info_in, info_out)
        self.info_in = info_in
        self.info_out = info_out
        self.node = info_out.origin
        self.network = info_out.network
        self.info_in_uuid = info_in.uuid
        self.info_out_uuid = info_out.uuid
        self.node_uuid = info_out.origin_uuid
        self.network_uuid = info_out.network_uuid

    def check_for_transformation(self, info_in, info_out):
        # check the infos are Infos.
        if not isinstance(info_in, Info):
            raise TypeError("{} cannot be transformed as it is a {}".format(info_in, type(info_in)))
        if not isinstance(info_out, Info):
            raise TypeError("{} cannot be transformed as it is a {}".format(info_out, type(info_out)))

        node = info_out.origin
        # check the info_in is from the node or has been sent to the node
        if not ((info_in.origin != node) or (info_in not in [t.info for t in node.transmissions(direction="incoming", status="received")])):
            raise ValueError("{} cannot transform {} as it has not been sent it or made it.".format(node, info_in))
