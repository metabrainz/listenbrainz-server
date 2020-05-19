BEGIN;

-- Returns sorted UUID array
CREATE OR REPLACE FUNCTION array_sort(uuid[])
RETURNS uuid[] AS $sorted_array$
DECLARE
    sorted_array uuid[];
BEGIN
    SELECT ARRAY(SELECT unnest($1) ORDER BY 1) INTO sorted_array;
    RETURN sorted_array;
END
$sorted_array$ LANGUAGE plpgsql IMMUTABLE;

-- Returns an sorted UUID array for an input JSON array
CREATE OR REPLACE FUNCTION convert_json_array_to_sorted_uuid_array(jsonb)
RETURNS uuid[] AS $converted_array$
DECLARE
    converted_array uuid[];
BEGIN
    SELECT public.array_sort(array_agg(elements)::uuid[]) || ARRAY[]::uuid[] INTO converted_array
    FROM jsonb_array_elements_text($1) elements;
    RETURN converted_array;
END
$converted_array$ LANGUAGE plpgsql IMMUTABLE;

COMMIT;
