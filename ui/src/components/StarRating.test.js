import React from 'react'
import { render, fireEvent, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import StarRating from './StarRating'

// Mock the SVG components to be accessible and identifiable
const MockStar = ({ alt, 'data-testid': testId, ...props }) => (
  <svg data-testid={testId} role="img" aria-label={alt} {...props} />
)

jest.mock('../static/images/star.svg', () => ({
  __esModule: true,
  default: 'star.svg',
  ReactComponent: (props) => <MockStar data-testid="star-filled" {...props} />,
}))
jest.mock('../static/images/star_outline.svg', () => ({
  __esModule: true,
  default: 'star_outline.svg',
  ReactComponent: (props) => <MockStar data-testid="star-outline" {...props} />,
}))

describe('StarRating', () => {
  test('renders 5 stars with correct aria-labels', () => {
    render(<StarRating starRating={0} />)
    for (let i = 1; i <= 5; i++) {
      // Use getByLabelText as it's more robust for SVGs with aria-label than getByAltText
      expect(screen.getByLabelText(`${i} stars`)).toBeInTheDocument()
    }
  })

  test('renders the correct number of filled and outline stars', () => {
    const { rerender } = render(<StarRating starRating={3} />)
    expect(screen.getAllByTestId('star-filled')).toHaveLength(3)
    expect(screen.getAllByTestId('star-outline')).toHaveLength(2)

    rerender(<StarRating starRating={5} />)
    expect(screen.getAllByTestId('star-filled')).toHaveLength(5)
    expect(screen.queryAllByTestId('star-outline')).toHaveLength(0)
  })

  test('calls onStarClick when a star is clicked (onMouseDown)', () => {
    const onStarClick = jest.fn()
    render(<StarRating starRating={0} onStarClick={onStarClick} />)

    // Click the 4th star
    const fourthStar = screen.getByLabelText('4 stars')
    fireEvent.mouseDown(fourthStar)

    expect(onStarClick).toHaveBeenCalledWith(4, expect.anything())
  })

  test('updates display on hover (onMouseEnter/onMouseLeave)', () => {
    const onStarClick = jest.fn() // onStarEnter/Leave logic only executes if onStarClick is provided
    render(<StarRating starRating={2} onStarClick={onStarClick} />)

    const fifthStar = screen.getByLabelText('5 stars')

    // Hover over the 5th star - should show all 5 as filled
    fireEvent.mouseEnter(fifthStar)
    expect(screen.getAllByTestId('star-filled')).toHaveLength(5)
    expect(screen.queryAllByTestId('star-outline')).toHaveLength(0)

    // Leave the star - should revert to 2 filled stars
    fireEvent.mouseLeave(fifthStar)
    expect(screen.getAllByTestId('star-filled')).toHaveLength(2)
    expect(screen.getAllByTestId('star-outline')).toHaveLength(3)
  })

  test('visibility logic with alwaysShow prop', () => {
    // When alwaysShow is false and rating is 0, opacity should be 0 (hidden)
    const { container, rerender } = render(
      <StarRating starRating={0} alwaysShow={false} />
    )
    expect(container.firstChild).toHaveStyle('opacity: 0')

    // When alwaysShow is true and rating is 0, opacity should be 1 (visible)
    rerender(<StarRating starRating={0} alwaysShow={true} />)
    expect(container.firstChild).toHaveStyle('opacity: 1')

    // When alwaysShow is false and rating > 0, opacity should be 1 (visible)
    rerender(<StarRating starRating={1} alwaysShow={false} />)
    expect(container.firstChild).toHaveStyle('opacity: 1')
  })

  test('renders in large mode without error', () => {
    const { container } = render(<StarRating starRating={3} large={true} />)
    // Verify it still renders 5 stars and handles the prop
    expect(container.firstChild).toBeInTheDocument()
    expect(screen.getAllByRole('img')).toHaveLength(5)
  })
})
