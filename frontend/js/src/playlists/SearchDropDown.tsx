import * as React from "react";
import { faUser } from "@fortawesome/free-solid-svg-icons";
import GlobalAppContext from "../utils/GlobalAppContext";
import ListenControl from "../listens/ListenControl";

export type SearchDropDownProps = {
  addCollaborator: (event: string) => void;
  userSearchResults: Array<string>;
};

export type SearchDropDownState = {};

export default class SearchDropDown extends React.Component<
  SearchDropDownProps,
  SearchDropDownState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;
  render() {
    const { userSearchResults, addCollaborator } = this.props;
    return (
      <div className="collaboratorsearchdropdown">
        {userSearchResults?.map((user) => {
          return (
            <ListenControl
              text={`${user}`}
              icon={faUser}
              action={() => {
                addCollaborator(user);
              }}
            />
          );
        })}
      </div>
    );
  }
}
