"""Generate master protobuf descriptors from the installed client's dump.cs.

Field-number/private-field analysis follows campus and SolisClient (AGPL-3.0).
The generated descriptor contains public game schema, never account credentials.
"""
import argparse
from pathlib import Path
import re
from google.protobuf import descriptor_pb2 as pb
from google.protobuf import descriptor_pool

PREFIX = 'Campus.Common.Proto.Client.'
GROUPS = ('Master', 'Common', 'Enums')
SCALARS = {name: getattr(pb.FieldDescriptorProto, 'TYPE_' + kind) for name, kind in {
    'double': 'DOUBLE', 'float': 'FLOAT', 'int': 'INT32', 'long': 'INT64',
    'uint': 'UINT32', 'ulong': 'UINT64', 'bool': 'BOOL', 'string': 'STRING',
    'ByteString': 'BYTES',
}.items()}


def generate(text):
    classes = {}
    enums = {}
    nested = []
    last_namespace = ''
    for block in re.split(r'^// Namespace: ', text, flags=re.M)[1:]:
        namespace, _, body = block.partition('\n')
        if namespace.strip():
            last_namespace = namespace.strip()
        group = namespace.strip().removeprefix(PREFIX)
        enum = re.search(r'^public enum ([\w.]+)\s', body, re.M)
        message = re.search(r'^public sealed class ([\w.]+) : .*\bIMessage\b', body, re.M)
        if not namespace.strip() and (enum or message):
            name = (enum or message)[1]
            if '.Types.' in name:
                nested.append((name, body, bool(enum), last_namespace.removeprefix(PREFIX)))
            continue
        if namespace.strip() != PREFIX + group or group not in GROUPS:
            continue
        if enum:
            enums[group, enum[1]] = body
        elif message:
            classes[group, message[1]] = body
    for name, body, is_enum, hint in nested:
        matches = [group for group in GROUPS if (group, name.split('.')[0]) in classes]
        if hint in matches:
            matches = [hint]
        if not matches:
            continue  # Nested types belonging to API or transaction schemas.
        if len(matches) != 1:
            raise ValueError(f'Ambiguous nested type {name}')
        (enums if is_enum else classes)[matches[0], name] = body
    file = pb.FileDescriptorProto(name='campus-client-master.proto', package='campus.schema', syntax='proto3')
    containers = {group: file.message_type.add(name=group) for group in GROUPS}
    for (group, name), body in sorted(enums.items()):
        enum = containers[group].enum_type.add(name=name.replace('.', '_'))
        values = re.findall(r'public const [\w.]+ (\w+) = (-?\d+);', body)
        if not values or not any(int(value) == 0 for _, value in values):
            raise ValueError(f'Enum has no zero value: {group}.{name}')
        if len({value for _, value in values}) != len(values):
            enum.options.allow_alias = True
        for value_name, number in values:
            enum.value.add(name=name.replace('.', '_') + '_' + value_name, number=int(number))
    field_count = 0
    for (group, name), body in sorted(classes.items()):
        message = containers[group].nested_type.add(name=name.replace('.', '_'))
        constants = list(re.finditer(r'public const int (\w+)FieldNumber = (\d+);', body))
        for index, constant in enumerate(constants):
            end = constants[index + 1].start() if index + 1 < len(constants) else body.find('// Properties', constant.end())
            section = body[constant.end():end if end >= 0 else len(body)]
            storage = re.search(r'private (?:readonly )?([\w.<> ,]+) (\w+_);', section)
            if not storage:
                raise ValueError(f'Cannot resolve field {group}.{name}.{constant[1]}')
            cs_type, field_name = storage.groups()
            field = message.field.add(name=field_name.removesuffix('_'), number=int(constant[2]), label=pb.FieldDescriptorProto.LABEL_OPTIONAL)
            repeated = re.fullmatch(r'RepeatedField<(.+)>', cs_type)
            if repeated:
                cs_type = repeated[1]
                field.label = pb.FieldDescriptorProto.LABEL_REPEATED
            if cs_type in SCALARS:
                field.type = SCALARS[cs_type]
            else:
                # Resolve C# generated names within their namespace first.
                matches = [(g, cs_type) for g in GROUPS if (g, cs_type) in classes or (g, cs_type) in enums]
                local = [key for key in matches if key[0] == group]
                if len(local) == 1:
                    matches = local
                if len(matches) != 1:
                    raise ValueError(f'Cannot resolve type {cs_type} in {group}.{name}: {matches}')
                target = matches[0]
                field.type = pb.FieldDescriptorProto.TYPE_ENUM if target in enums else pb.FieldDescriptorProto.TYPE_MESSAGE
                field.type_name = '.campus.schema.' + target[0] + '.' + target[1].replace('.', '_')
            field_count += 1
    descriptor_pool.DescriptorPool().Add(file)
    if ('Master', 'ProduceCharacterUnitOverrideLiveCostume') not in classes:
        raise ValueError('Current client master schema is missing')
    return file, len(classes), len(enums), field_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dump', type=Path, required=True)
    parser.add_argument('--patch', action='store_true', help='Emit an apply_patch payload instead of writing repository files')
    args = parser.parse_args()
    file, messages, enums, fields = generate(args.dump.read_text(encoding='utf-8-sig'))
    import base64
    import gzip
    encoded = base64.b64encode(gzip.compress(file.SerializeToString(), mtime=0)).decode('ascii')
    if args.patch:
        target = Path(__file__).parent / 'master' / 'client_schema.b64'
        print('*** Begin Patch\n*** Add File: ' + str(target))
        for offset in range(0, len(encoded), 120):
            print('+' + encoded[offset:offset + 120])
        print('*** End Patch')
    else:
        print(f'Messages={messages}, enums={enums}, fields={fields}, encoded bytes={len(encoded)}')


if __name__ == '__main__':
    main()
