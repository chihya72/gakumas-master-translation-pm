package master

import (
	"testing"

	"google.golang.org/protobuf/encoding/protowire"
	"google.golang.org/protobuf/proto"
	"google.golang.org/protobuf/reflect/protoreflect"
)

func TestNewClientTableAndUnknownWireFields(t *testing.T) {
	message := newTableMessage("ProduceCharacterUnitOverrideLiveCostume")
	row := protowire.AppendTag(nil, 1, protowire.BytesType)
	row = protowire.AppendString(row, "unit-test")
	if err := proto.Unmarshal(row, message); err != nil {
		t.Fatal(err)
	}
	if err := checkKnownFields(message.ProtoReflect()); err != nil {
		t.Fatal(err)
	}
	yaml, err := YamlMarshal(message)
	if err != nil || len(yaml) == 0 {
		t.Fatalf("cannot export current client table: %v", err)
	}
	// A future field is valid protobuf, so ordinary Unmarshal alone succeeds.
	row = protowire.AppendTag(row, 9999, protowire.VarintType)
	row = protowire.AppendVarint(row, 1)
	if err := proto.Unmarshal(row, message); err != nil {
		t.Fatal(err)
	}
	if err := checkKnownFields(message.ProtoReflect()); err == nil {
		t.Fatal("future wire field would be silently dropped by YAML")
	}
}

func TestUnknownFieldsInNestedMasterData(t *testing.T) {
	message := newTableMessage("ProduceCard").ProtoReflect()
	field := message.Descriptor().Fields().ByName("produceDescriptions")
	if field == nil || !field.IsList() || field.Message() == nil {
		t.Fatal("nested descriptions missing")
	}
	list := message.Mutable(field).List()
	nested := list.NewElement().Message()
	unknown := protowire.AppendTag(nil, 9999, protowire.VarintType)
	nested.SetUnknown(protowire.AppendVarint(unknown, 1))
	list.Append(protoreflect.ValueOfMessage(nested))
	if err := checkKnownFields(message); err == nil {
		t.Fatal("nested future wire field would be silently dropped by YAML")
	}
}
