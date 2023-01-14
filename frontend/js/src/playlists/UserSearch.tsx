import * as React from "react";
import { faUser } from "@fortawesome/free-solid-svg-icons";
import GlobalAppContext from "../utils/GlobalAppContext";
import ListenControl from "../listens/ListenControl";

export type UserSearchProps = {
  userClick: (event: string) => void;
  placeholder: string;
};

export type UserSearchState = {
  newUser: string;
  userSearchResults: Array<any>;
};

export default class UserSearch extends React.Component<
  UserSearchProps,
  UserSearchState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: UserSearchProps) {
    super(props);
    this.state = {
      newUser: "",
      userSearchResults: [],
    };
  }

  componentDidUpdate(prevProps: UserSearchProps, prevState: UserSearchState) {
    const { newUser } = this.state;

    if (prevState.newUser !== newUser) {
      this.searchUsers();
    }
  }

  handleInputChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { target } = event;
    const value =
      target.type === "checkbox"
        ? (target as HTMLInputElement).checked
        : target.value;
    const { name } = target;
    // @ts-ignore
    this.setState({
      [name]: value,
    });
  };

  searchUsers = async () => {
    const { currentUser, APIService } = this.context;
    const { newUser } = this.state;
    const response = await APIService.searchUsers(
      newUser,
      currentUser.auth_token
    );
    this.setState({
      userSearchResults: response.users,
    });
  };

  render() {
    const { newUser, userSearchResults } = this.state;
    const { placeholder, userClick } = this.props;
    return (
      <div>
        <input
          type="text"
          className="form-control"
          name="newUser"
          onChange={this.handleInputChange}
          placeholder={placeholder}
          value={newUser}
        />
        <div className="search-dropdown">
          {userSearchResults?.map((user) => {
            return (
              <ListenControl
                text={`${user[0]}`}
                icon={faUser}
                action={() => {
                  userClick(user[0]);
                  this.setState({
                    newUser: "",
                    userSearchResults: [],
                  });
                }}
              />
            );
          })}
        </div>
      </div>
    );
  }
}
