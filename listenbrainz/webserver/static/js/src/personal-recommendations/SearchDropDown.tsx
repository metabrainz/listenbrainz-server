import * as React from "react";
import { faUser } from "@fortawesome/free-solid-svg-icons";
import ListenControl from "../listens/ListenControl";

export type SearchDropDownProps = {
  action: (event: string) => void;
  suggestions?: Array<string> | null;
};

const SearchDropDown = (props: SearchDropDownProps) => {
  const { suggestions, action } = props;
  return (
    <div className="searchdropdown">
      {suggestions!.map((name) => {
        return (
          <ListenControl
            text={name}
            action={() => {
              action(name);
            }}
            icon={faUser}
          />
        );
      })}
    </div>
  );
};

export default SearchDropDown;
