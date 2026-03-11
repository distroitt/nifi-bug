from nifiapi.flowfiletransform import FlowFileTransform, FlowFileTransformResult
from nifiapi.relationship import Relationship


class ReproProcessorGamma(FlowFileTransform):
    class ProcessorDetails:
        version = "1.0.0"
        description = "Synthetic processor used to reproduce Python bridge startup issues."
        tags = ["repro", "py4j", "python", "nifi"]

    class Java:
        implements = ["org.apache.nifi.python.processor.FlowFileTransform"]

    def __init__(self, **kwargs):
        self.relationships = [
            Relationship(name="success", description="Successful transform"),
            Relationship(name="failure", description="Failed transform"),
        ]
        self.descriptors = []

    def getPropertyDescriptors(self):
        return self.descriptors

    def getRelationships(self):
        return self.relationships

    def transform(self, context, flowfile):
        return FlowFileTransformResult(
            relationship="success",
            contents=flowfile.getContentsAsBytes(),
            attributes={},
        )
