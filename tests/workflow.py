CUSTOM_NODE_TEMPLATE = """
from deepomatic.workflows.nodes import CustomNode
class MyNode(CustomNode):
    def __init__(self, config, node_name, input_nodes, concepts):
        super(MyNode, self).__init__(config, node_name, input_nodes)
    def process(self, context, regions):
        return regions
"""


WORKFLOW_YAML_TEMPLATE = """
version: 1.1
workflow_name: test

workflow:
  entries:
    - name: test_image
      data_type: Image

  outcomes:
    - name: number_of_b
      output_of: b_counter
      concept:
        name: b_count
        type: Number

  steps:
    - name: detector_a
      type: Inference
      inputs:
        - test_image
      args:
        model_id: 51863
        concepts:
          - a

    - name: detector_b
      type: Inference
      inputs:
        - test_image
      args:
        model_id: 51863
        concepts:
          - b

    - name: b_counter
      type: Counter
      inputs:
        - detector_b
      args:
        entry: test_image
        concept_name: b
"""
