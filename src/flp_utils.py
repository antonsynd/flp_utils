import collections
import logging

_logger = logging.getLogger('flp')

# 2020-09-18: Works with 20.7.1.1173 (Windows)

def dump_version(data):
    '''
    Dumps the version string of the FLP file.

    @param data: byte string of the FLP file
    '''
    # 100 byte end is arbitrary, but the version number should be before then
    version_prefix_index = data.find(b'\x00\xc7\x0c', 0, 100)

    if version_prefix_index < 0:
        _logger.debug('no version prefix found')
        return None

    version_index = version_prefix_index + 3

    null_byte_index = data.find(b'\x00', version_index)

    if null_byte_index < 0:
        _logger.debug('null byte not found')
        return None

    return data[version_index:null_byte_index].decode()

def dump_audio_files(data, paths=None):
    '''
    Dumps the paths of all audio files referenced in the FLP in a list.

    @param data: byte string of the FLP file
    @param paths: optional dict of FL path variables to paths

    Common ones include:
        %USERPROFILE%
        %FLStudioFactoryData%
        %FlStudioUserData%
    '''
    audio_file_paths = collections.OrderedDict()

    data_pos = 0
    data_num_bytes = len(data)

    while data_pos < data_num_bytes:
        audio_pre_prefix_index = data.find(b'\x14\x00', data_pos)

        if audio_pre_prefix_index < 0:
            _logger.debug('no audio prefix found')
            break

        data_pos = audio_pre_prefix_index + 2

        audio_path_prefix_index = data.find(b'\x01', data_pos)

        if audio_path_prefix_index < 0:
            _logger.debug('no leading byte found')
            continue

        partial_prefix_length = audio_path_prefix_index - audio_pre_prefix_index

        # Arbitrary set to 6 to find the path should be enough
        # the longest I've seen is Äò \xc3\x84\xc3\xb2
        if partial_prefix_length > 6:
            _logger.debug('partial prefix length '
                'too long: {}'.format(partial_prefix_length))
            continue

        audio_path_index = audio_path_prefix_index + 1

        audio_path_suffix_index = data.find(b'\x00\x00', audio_path_index)

        if audio_path_suffix_index < 0:
            _logger.debug('no audio path suffix found')
            break

        # TODO: It's possible the paths are stored in double byte encoding and
        # all my paths happen to be in ASCII
        audio_file_path = data[audio_path_index:audio_path_suffix_index:2].decode()

        if audio_file_path[0] == '%':
            for k, v in paths.items():
                if audio_file_path.startswith(k):
                    audio_file_path = audio_file_path.replace(k, v, 1)
                    break

        if audio_file_path:
            audio_file_paths[audio_file_path] = None

        data_pos = audio_path_suffix_index + 2

    return list(audio_file_paths.keys())
