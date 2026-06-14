from typing import Protocol


class P_Serializer(Protocol):
    @classmethod
    def serialize(cls, obj, bm): ...

    @classmethod
    def deserialize(cls, obj, bm, clipboard): ...

    @classmethod
    def _serialize_layer_collection(cls, elements, layer_collection, layer_type):
        """
        Serialize a single BMesh layer collection.

        elements:
            bm.verts / bm.edges / bm.faces

        layer_collection:
            bm.edges.layers.float
            bm.faces.layers.int
            ...

        layer_type:
            "float", "int", ...
        """

        result = {}

        for layer in layer_collection.values():
            values = []
            for elem in elements:
                value = elem[layer]

                if hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
                    value = tuple(value)

                values.append(value)

            result[layer.name] = {
                "type": layer_type,
                "values": values,
            }

        return result
