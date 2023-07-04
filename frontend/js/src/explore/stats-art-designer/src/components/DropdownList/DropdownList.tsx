import "./DropdownList.css";
type DropdownListProps ={
  opts:Array<Array<string>>;
  onChange: (event: React.ChangeEvent<HTMLSelectElement>) => void;
  value:string;
}

const DropdownList = ({opts, onChange, value}: DropdownListProps) => {
  return (
    <select className="dropdown-list" value={value} onChange={onChange}>
      {opts.map((opt) => <option key={opt[0]} value={opt[0]}>{opt[1]}</option>)}
    </select>
  )
}

export default DropdownList;