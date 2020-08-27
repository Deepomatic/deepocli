from deepomatic.workflows.nodes import CustomNode


class MyNode(CustomNode):
    def __init__(self, config, node_name, input_nodes, concepts):
        super(MyNode, self).__init__(config, node_name, input_nodes)

    def process(self, context, regions):
        return regions
