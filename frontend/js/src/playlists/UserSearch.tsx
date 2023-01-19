import * as React from "react";
import { faUser } from "@fortawesome/free-solid-svg-icons";
import { throttle as _throttle } from "lodash";
import debounceAsync from "debounce-async";
import GlobalAppContext from "../utils/GlobalAppContext";
import ListenControl from "../listens/ListenControl";

export type UserSearchProps = {
  userClick: (event: string) => void;
  placeholder: string;
  disabled: boolean;
};

export type UserSearchState = {
  newUser: string;
  userSearchResults: Array<SearchUser>;
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

  

  handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    this.setState(
      {
        newUser: event.target.value,
      },
      () => {
        this.searchUsers();
      }
    );
  };

  // eslint-disable-next-line react/sort-comp
  throttledHandleInputChange = _throttle(this.handleInputChange, 300);

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

  

  handleResultClick = (user: string) => {
    const { userClick } = this.props;
    userClick(user);
    this.setState({
      newUser: "",
      userSearchResults: [],
    });
  };

  render() {
    const { newUser, userSearchResults } = this.state;
    const { placeholder, userClick, disabled } = this.props;
    return (
      <div>
        <input
          type="text"
          className="form-control"
          name="newUser"
          onChange={this.throttledHandleInputChange}
          placeholder={placeholder}
          value={newUser}
        />
        <div className="search-dropdown">
          {userSearchResults?.map((user) => {
            return (
              <ListenControl
                text={`${user.user_name}`}
                icon={faUser}
                 // eslint-disable-next-line react/jsx-no-bind
                action={this.handleResultClick.bind(this, user.user_name)}
                disabled={disabled}
              />
            );
          })}
        </div>
      </div>
    );
  }
}
