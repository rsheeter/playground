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

### Feature based matching

TODO why is this important? supporting data

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

### Italic and slant
