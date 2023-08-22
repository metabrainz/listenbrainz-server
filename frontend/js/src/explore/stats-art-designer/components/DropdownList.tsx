import * as React from "react";

type DropdownListProps = {
  opts: Array<Array<string>>;
  onChange: (event: React.ChangeEvent<HTMLSelectElement>) => void;
  value: string;
  id?: string;
};

function DropdownList({ opts, onChange, value, id }: DropdownListProps) {
  return (
    <select
      id={id ?? "dropdown"}
      className="form-control"
      value={value}
      onChange={onChange}
    >
      {opts.map((opt) => (
        <option key={opt[0]} value={opt[0]}>
          {opt[1]}
        </option>
      ))}
    </select>
  );
}

export default DropdownList;
