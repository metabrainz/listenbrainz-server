import * as React from "react";
import { faUser } from "@fortawesome/free-solid-svg-icons";
import GlobalAppContext from "../utils/GlobalAppContext";
import ListenControl from "../listens/ListenControl";

export type SearchDropDownProps = {
  action: (event: string) => void;
  searchResults: Array<string>;
};

export type SearchDropDownState = {};

export default class SearchDropDown extends React.Component<
  SearchDropDownProps,
  SearchDropDownState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;
  render() {
    const { searchResults, action } = this.props;
    return (
      <div className="collaboratorsearchdropdown">
        {searchResults?.map((user) => {
          return (
            <ListenControl
              text={`${user}`}
              icon={faUser}
              action={() => {
                action(user);
              }}
            />
          );
        })}
      </div>
    );
  }
}
