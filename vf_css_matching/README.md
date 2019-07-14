# CSS style matching difficulties

Google Fonts strives to have users "pay" (in bytes and resulting latency) only for the parts of fonts they actually use. As [CSS3](https://www.w3.org/TR/css-fonts-3/#font-face-rule) puts it "Using CSS font matching rules, a user agent can selectively download only those faces that are needed for a given piece of text."

We are encountering problems with the current [style matching algorithm](https://www.w3.org/TR/css-fonts-4/#font-style-matching) in several areas:

1.  Feature-based matching
1.  Variable font matching on arbitrary axes
1.  Variable font matching for named instances
1.  Matching italic + slant (spec seems to think of them as exclusive choices)

This document outlines potential changes to the style matching algorithm to address each area. "Variable fonts" is abbreviated "VF" throughout.

## Current style matching
The CSS4 [style matching algorithm](https://www.w3.org/TR/css-fonts-4/#font-style-matching) is roughly:

```
Step 1: Take the first value from the computed font-family property of element
Step 2: If family name is a generic keyword, resolve it
Step 3: If family name is NOT a generic keyword find font faces
    Search @font-face rules then installed fonts

NOTE: we're only interested in the @font-face case in this document

Step 4: Pick a specific @font-face. 
    A VF matches as the position with the best matching characteristics.

4.0 Start with the set of @font-face that match by family name 
4.1 Find the set of faces that match best by width (font-stretch), discard others
    font-stretch supports % so we have fine-grained matching on ‘wdth’
4.2 Find the set of faces that match best by style (font-style), discard others
    font-style can only match 0/1 on ‘ital’ using normal|italic
    oblique has fine grained specification that presumably can match ‘slnt’ 
4.3, 4.4 are curiously not used in spec, omitting here to make #s align
4.5 Find the set of faces that match best by weight (font-weight), discard others
    Font-weight supports int [1,1000] so we have fine-grained matching on ‘wght’
4.6 font-size must be matched within UA-selected tolerance
    TODO what does this actually mean?
4.7 unicode-range: pick the highest priority (declared last) matching face
    Match if effective character map contains the char
    NOTE: 4.7 always narrows the search to 0 or 1 @font-face
4.8 Fallback by family name
   If no matching face exists try the next family name, starting at Step 1
4.9 Fallback however you like
  If no matching face exists, perform UA-specific fallback
4.10 Capsize
  Indicate failure in a UA-specific way, such as by rendering notdef
```

Note that the selection of @font-face is limited to {family name, width, style, weight}; this will come back to bite us below :)

@font-face can contain variation settings, but they come into play only after selection as part of [rendering](https://www.w3.org/TR/css-fonts-4/#font-rend-desc).

## Limitations and proposed changes

Changes aim to increase the range of scenarios where only the content that is needed gets downloaded.

### Variable font axis matching

**Motivation** Variable fonts size increases substantially (roughly `2^#axes` in some cases) as axes are added.

There are cases where sending instances is much cheaper (in file size) than sending a whole variable font. For example, imagine that the font family A has `wdth` and `wght` axes, and it's size doubles for each (that is, the entire variable font is 4x the size of a typical instance). If a user wants Light, Expanded and Regular, Normal (two positions in the two-dimensional space) then cost in bytes for fonts is halved by sending two instances vs the single variable font.

TODO link to VF size data

**CSS issue** We can't match on arbitrary axes:

```css
/**
 * This face is unreachable: any matching algorithm hit would match both faces
 * and then pick the second one (per 4.7)
 */
@font-face {
  font-family: “A”;
  font-variation-settings: “GRAD” 0
}

/**
 * If these faces match, this one always wins under rule 4.7
 * Equal priority, last declaration wins
 */
@font-face {
  font-family: “A”;
  font-variation-settings: “GRAD” 1
}
```

**Suggested solution** TODO exact suggested fix :)


### Italic and Slant

**Motivation** Use of `ital` and `slnt` axes should be simple.

**CSS issue** Today `ital` behaves inconsistently.

Jason Pamental wrote this up in [state of Italics in variable font](https://mailchi.mp/444e7a454775/web-typography-news-20-contextual-stylistics-and-other-fake-band-names). A few main problems seem to pop out:

1.  It's impossible to declare a *range* of italic with `font-style`
    1.  [Roslindale](https://djr.com/notes/roslindale-variable-italic-font-of-the-month/) shows that there is more possible with `ital` than a binary on/off.
1.  Browsers may synthesize italic *on top of italic* in some situations; this seems like it's purely a bug
    1.  `font-style: oblique 0deg 20deg;` should **not** enable the Italic axis
1.  It's impossible to declare italic *and* slant on the same font using `font-style`

We ideally need `font-style` to permit ranges of both italic and slant together, and matching to accomodate.

**Suggested solution (short term)**

1.   Specify that if an element is styled `italic` and it matches a font with an `ital` axis then `ital` should be set to the largest supported value <= 1 and no synthesis of italic should occur. 
1.   Specify that if an element is styled `normal` and it matches a font with an `ital` axis then `ital` should be set to the min supported value >= 0.

Example:

```css
/** Assume my-vf.woff2 supports ital 0.25-0.75
@font-face {
  src: url('my-vf.woff2') format("woff2-variations");
  font-family: 'A';
}

/* Element styled use-norm should render using 'ital' 0.25 and NOT perform synthesis */
.use-norm {
  font-family: 'A'
}

/* Element styled use-norm should render using 'ital' 0.75 and NOT perform synthesis */
.use-ital {
  font-family: 'A'
  font-style: italic;
}
```

**Suggested solution (long term)**

Allow an optional range of italic to be specified for [font-style](https://drafts.csswg.org/css-fonts-4/#descdef-font-face-font-style):

```
OLD: Value: auto | normal | italic | oblique [<angle> | <angle> <angle>]?
NEW: Value: auto | normal | [[italic [<ital> | <ital> <ital>]?] [oblique [<angle> | <angle> <angle>]?]]]!

<ital> should be a value in [0, 1] (the 'ital' axis space).

This allows font-style to express a region in the 2d space of ital,slnt:

font-style: normal oblique;
font-style: italic oblique;
font-style: italic 0 1 oblique -89 89;
font-style: italic 0.3 0.7 oblique 0 15;
```

[font-style](https://drafts.csswg.org/css-fonts-4/#propdef-font-style) for elements values can remain unchanged because ital 0/1 is expected to be by far the most common usage. Values would have the following meanings:

```
normal            Matches a face that is neither italic nor oblique. That is matches as italic 0, oblique 0.
italic            Matches a face with any non-0 italic, or non-0 oblique if no face declaring italic exists.
oblique <angle>?  Matches as before
```

### Variable font named instance matching

**Motivation** Variable fonts size increases substantially (roughly `2^#axes` in some cases) as axes are added.

A user may wish to use named instances that are positioned in variation space such that sending instances would be cheaper than an entire variable font. A user may wish to use multiple instances from a single face, currently this is tiresome to achieve.

**CSS issue** We can't use multiple instances from a given `@font-face`

[font-named-instance](https://www.w3.org/TR/css-fonts-4/#font-named-instance) permits a single named instance for an `@font-face`. [feature-variation-precedence](https://www.w3.org/TR/css-fonts-4/#feature-variation-precedence) allows the named instance to be applied.

Named instances do not participate in *matching* at all. This makes use of multiple named instances awkward:

1.  We can't use multiple named instances on an unregistered axis
  1.  For `ital` we can access two positions
1.  We have to matching `@font-face` by other attributes to reach a named instance

Consider this sketch:

```css
/**
 * This face is unreachable: any matching algorithm hit would match both faces
 * and then pick the second one (per 4.7)
 */
@font-face {
  font-family: “A”;
  font-named-instance: "first";
}

@font-face {
  font-family: “A”;
  font-named-instance: "second";
}

/* this is illegal; would be nice if it wasn't */
.use-first {
  font-named-instance: "first"
}

/**
 * Even better: full control over fallback using instances
 * named-instance (instance-name, family-name), valid in font-family list
 */
.prefer-first {
  font-family: named-instance("first", "A"), "Lobster", named-instance("second", "A");
}
```

Ideally font-named-instance would be legal on all elements and allow multiple values in a fallback chain that included family name at each step (use "Bold" instance of "Roboto", failing that the "Medium" instance of "Open Sans").

On @font-face we would want multiple names as well, either via font-family list or allowing a font-named-instance list.

**Suggested solution** TODO exact suggested fix :)

### Variant based matching

TODO why is this important? supporting data

**Motivation** Make it possible to deliver specialized content only to users that need it.

At render-time we know quite a lot about what features of the font are desired. Unfortunately we can't use any of this at matching time. If features could participate in matching we could subset fonts based on feature and match only the ones in use. For example:

```css
/* Only downloads if text exists that wants family "A", small-caps */
@font-face {
  font-family: “A”;
  font-variant: small-caps;
  src: url(A-small-caps.woff2);
}

/* Downloads for any non-small-caps use of A */
@font-face {
  font-family: “A”;
  src: url(A.woff2);
}
```
**CSS issue** We can't match on features

**Suggested solution** Insert a new matching step.

```
4.5 Find the set of faces that match best by weight (font-weight), discard others
    Font-weight supports int [1,1000] so we have fine-grained matching on ‘wght’
**NEW** Find the set of faces that match best by feature
4.6 font-size must be matched within UA-selected tolerance
```

Allow font-variant to be specified on `@font-face`.

During matching insert a new step between 4.5 and 4.6:

1.  Collect font-variant (including subproperties) values for the element
1.  Match `@font-face` that have any of the `font-variant` values for the element and `@font-face` rules that don't set `font-variant` at all

In the example above a run of small-cap text will match both faces, then select the small-caps variant as higher priority in step 4.7. Text that uses font-family A that doesn't use small-caps will match the font-variant'less `@font-face`.
