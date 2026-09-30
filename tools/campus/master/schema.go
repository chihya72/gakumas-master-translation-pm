package master

import (
	"bytes"
	"compress/gzip"
	_ "embed"
	"encoding/base64"
	"fmt"
	"io"
	"strings"
	"unicode"

	"google.golang.org/protobuf/proto"
	"google.golang.org/protobuf/reflect/protodesc"
	"google.golang.org/protobuf/reflect/protoreflect"
	"google.golang.org/protobuf/types/descriptorpb"
	"google.golang.org/protobuf/types/dynamicpb"
)

// Extracted from Android client 3.4.1. Regenerate with schema_from_dump.py
// when a client update adds or changes master tables or fields.
//
//go:embed client_schema.b64
var encodedClientSchema string

var masterSchema = loadMasterSchema()

func loadMasterSchema() protoreflect.MessageDescriptors {
	encoded := strings.Map(func(r rune) rune {
		if unicode.IsSpace(r) {
			return -1
		}
		return r
	}, encodedClientSchema)
	compressed, err := base64.StdEncoding.DecodeString(encoded)
	if err != nil {
		panic(err)
	}
	reader, err := gzip.NewReader(bytes.NewReader(compressed))
	if err != nil {
		panic(err)
	}
	defer reader.Close()
	data, err := io.ReadAll(io.LimitReader(reader, 16*1024*1024))
	if err != nil {
		panic(err)
	}
	file := &descriptorpb.FileDescriptorProto{}
	if err := proto.Unmarshal(data, file); err != nil {
		panic(err)
	}
	descriptor, err := protodesc.NewFile(file, nil)
	if err != nil {
		panic(err)
	}
	master := descriptor.Messages().ByName("Master")
	if master == nil {
		panic("client schema has no master definitions")
	}
	return master.Messages()
}

func HasTable(name string) bool {
	return masterSchema.ByName(protoreflect.Name(name)) != nil
}

func newTableMessage(name string) proto.Message {
	descriptor := masterSchema.ByName(protoreflect.Name(name))
	if descriptor == nil {
		panic(fmt.Sprintf("unsupported master table %s: update client schema", name))
	}
	return dynamicpb.NewMessage(descriptor)
}

// proto.Unmarshal preserves unknown fields, but JSON/YAML would omit them.
// Check the actual decoded row before publishing an incomplete snapshot.
func checkKnownFields(message protoreflect.Message) error {
	if len(message.GetUnknown()) != 0 {
		return fmt.Errorf("unrecognized fields in %s: update client schema", message.Descriptor().FullName())
	}
	var result error
	message.Range(func(field protoreflect.FieldDescriptor, value protoreflect.Value) bool {
		if field.Message() == nil {
			return true
		}
		if field.IsList() {
			list := value.List()
			for i := 0; i < list.Len(); i++ {
				if err := checkKnownFields(list.Get(i).Message()); err != nil {
					result = err
					return false
				}
			}
		} else {
			result = checkKnownFields(value.Message())
		}
		return result == nil
	})
	return result
}
