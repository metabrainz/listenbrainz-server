/* eslint-disable jsx-a11y/anchor-is-valid */
import * as React from 'react'

type PagerItemProps = {
    className: string;
    children: string;
    style?: object;
    onClick: (event: React.SyntheticEvent) => any;
    onKeyDown: (event: React.KeyboardEvent) => any;
}
type PagerProps = {
    children: React.ReactElement[];
}
const Pager = ({ children }: PagerProps) => {

    return (
        <ul className="pager" style={{ display: "flex" }}>
            {children}
        </ul>
    )
}

const Item = (props: PagerItemProps) => {
    const { className, onClick, onKeyDown, children } = props;

    return (
        <li
            className={className}
        >
            <a
                role="button"
                onClick={onClick}
                onKeyDown={onKeyDown}
                tabIndex={0}
            >
                {children}
            </a>
        </li>
    )
};
export { Pager, Item };