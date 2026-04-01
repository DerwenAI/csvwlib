import dateutil.parser


class TypeConverter:

    @staticmethod
    def convert_if_necessary(value, column_metadata):
        if 'datatype' not in column_metadata or not isinstance(column_metadata['datatype'], dict):
            return value

        return TypeConverter.convert(value, column_metadata['datatype'])

    @staticmethod
    def convert(value, datatype):
        type_name = TypeConverter.get_type_name(datatype)
        return {
            'boolean': lambda: TypeConverter._convert_boolean(value, datatype),
            'date': lambda: TypeConverter._convert_date(value).__str__(),
            'datetime': lambda: TypeConverter._convert_datetime(value, datatype.get('format', '')),
            'dateTime': lambda: TypeConverter._convert_datetime(value, datatype.get('format', '')),
            'dateTimeStamp': lambda: TypeConverter._convert_datetime_timestamp(value).__str__(),
            'decimal': lambda: float(value),
            'double': lambda: float(value),
            'float': lambda: float(value),
            'integer': lambda: int(value),
            'number': lambda: float(value),
            'time': lambda: TypeConverter._convert_time(value, datatype.get('format', ''))
        }.get(type_name, lambda: value)()

    @staticmethod
    def get_type_name(datatype_entry):
        if type(datatype_entry) is dict:
            return datatype_entry.get('base', 'string')
        else:
            return datatype_entry

    @staticmethod
    def _convert_datetime_timestamp(datatime_string):
        if datatime_string.endswith('Z'):
            return datatime_string
        return dateutil.parser.parse(datatime_string).isoformat()

    @staticmethod
    def _convert_date(date_string):
        if len(date_string) > 12:
            return date_string
        if date_string.endswith('Z'):
            date_string = date_string.replace(' ', '')
            date_string = date_string[:-1]
            date_string = date_string.replace('.', '-')
            date_string = date_string.replace('/', '-')
            parts = date_string.split('-')
            if len(parts[0]) == 2:
                date_string = '-'.join([parts[2], parts[1], parts[0]])
            date_string += 'Z'
            return date_string
        else:
            return dateutil.parser.parse(date_string).date()

    @staticmethod
    def _convert_datetime(datetime_string, format_string):
        datetime = dateutil.parser.parse(datetime_string).isoformat().__str__()
        if format_string.endswith('S'):
            datetime = TypeConverter._strip_trailing_zeros(datetime)
        return datetime.replace('+00:00', 'Z')

    @staticmethod
    def _convert_time(time_str, time_format):
        time = time_str
        if ':' not in time_str:
            time = time_str.split(' ')[0]
            time = [time[i:i+2] for i in range(0, len(time), 2)]
            time = ':'.join(time)
        if ' ' in time_str:
            time = time + time_str.split(' ')[1]
        parsed = dateutil.parser.parse(time).timetz().__str__()
        if time_format.endswith('S'):
            parsed = TypeConverter._strip_trailing_zeros(parsed)
        return parsed.replace('+00:00', 'Z')

    @staticmethod
    def _strip_trailing_zeros(string):
        offset = 0
        for char in reversed(string):
            if char != '0':
                break
            offset -= 1
        offset = offset if offset < 0 else None
        return string[:offset]

    @staticmethod
    def _convert_boolean(string, datatype_metadata):
        if 'format' not in datatype_metadata:
            if string.isdigit():
                return bool(int(string))
            else:
                if string == 'true':
                    return True
                elif string == 'false':
                    return False
                else:
                    return string

        true_template, false_template = datatype_metadata['format'].split('|')
        if string == true_template:
            return True
        elif string == false_template:
            return False
        else:
            return string
