from wallace import processes, networks, nodes, db, models
from wallace.nodes import Agent


class TestProcesses(object):

    def setup(self):
        self.db = db.init_db(drop_all=True)

    def teardown(self):
        self.db.rollback()
        self.db.close()

    def test_random_walk_from_source(self):

        net = models.Network()

        agent1 = nodes.ReplicatorAgent()
        agent2 = nodes.ReplicatorAgent()
        agent3 = nodes.ReplicatorAgent()

        net.add(agent1)
        net.add(agent2)
        net.add(agent3)
        self.db.add(agent1)
        self.db.add(agent2)
        self.db.add(agent3)
        self.db.commit()

        agent1.connect_to(agent2)
        agent2.connect_to(agent3)

        source = nodes.RandomBinaryStringSource()
        net.add(source)
        self.db.add(source)
        self.db.commit()

        source.connect_to(net.nodes(type=Agent)[0])
        source.create_information()

        processes.random_walk(net)

        agent1.receive()
        msg = agent1.infos()[0].contents

        processes.random_walk(net)
        agent2.receive()
        agent2.infos()[0].contents

        processes.random_walk(net)
        agent3.receive()
        agent3.infos()[0].contents

        assert msg == agent3.infos()[0].contents

    def test_moran_process_cultural(self):

        # Create a fully-connected network.
        net = models.Network()

        agent1 = nodes.ReplicatorAgent()
        agent2 = nodes.ReplicatorAgent()
        agent3 = nodes.ReplicatorAgent()
        self.db.add_all([agent1, agent2, agent3])
        net.add([agent1, agent2, agent3])
        self.db.commit()

        agent1.connect_to(agent2)
        agent1.connect_to(agent3)
        agent2.connect_to(agent1)
        agent2.connect_to(agent3)
        agent3.connect_to(agent1)
        agent3.connect_to(agent2)

        # Add a global source and broadcast to all the nodes.
        source = nodes.RandomBinaryStringSource()
        self.db.add(source)
        net.add(source)
        for agent in net.nodes(type=Agent):
            source.connect_to(agent)
            source.transmit(to_whom=agent)
            agent.receive()

        # Run a Moran process for 100 steps.
        for i in xrange(100):
            processes.moran_cultural(net)
            for agent in net.nodes(type=Agent):
                agent.receive()

        # Ensure that the process had reached fixation.
        assert agent1.infos()[-1].contents == agent2.infos()[-1].contents
        assert agent2.infos()[-1].contents == agent3.infos()[-1].contents
        assert agent3.infos()[-1].contents == agent1.infos()[-1].contents

    def test_moran_process_sexual(self):

        # Create a fully-connected network.
        net = networks.Network()
        self.db.add(net)

        agent1 = nodes.ReplicatorAgent(network=net)
        agent2 = nodes.ReplicatorAgent(network=net)
        agent3 = nodes.ReplicatorAgent(network=net)

        agent1.connect(direction="both", other_node=[agent2, agent3])
        agent2.connect(direction="both", other_node=agent3)

        # Add a global source and broadcast to all the nodes.
        source = nodes.RandomBinaryStringSource(network=net)
        source.connect(direction="to", other_node=net.nodes(type=Agent))

        source.create_information()

        for agent in net.nodes(type=Agent):
            source.transmit(to_whom=agent)
            agent.receive()

        # Run a Moran process for 100 steps.
        for i in range(100):
            nodes.ReplicatorAgent(network=net)
            processes.moran_sexual(net)
            for agent in net.nodes(type=Agent):
                agent.receive()

        # Ensure that the process had reached fixation.
        assert agent1.status == "dead"
        assert agent2.status == "dead"
        assert agent3.status == "dead"

        for a in net.nodes(type=Agent):
            for a2 in net.nodes(type=Agent):
                assert a.infos()[0].contents == a2.infos()[0].contents
