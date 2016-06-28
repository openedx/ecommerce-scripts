
#  Instructions for configuring GTM for edX Sailthru integration

 These are configuration instructions for setting up GTM to capture activity for Sailthru at edX.  There is a change
 to template.php in edx_mktg to insert a meta field which provides the Sailthru interest tag information for most of the
 pages.  An example is:

  \<meta name="sailthru.tags" content="subject-economics-finance" /\>
 
## Variables

 Two user defined variables must be added to GTM of type Data Layer Variable: 
 
| Field            | Value                                                                          |
|------------------|--------------------------------------------------------------------------------|
| Name:            | category                                                                       |
| Type:            | Data Layer Variable                                                            |
| Variable name:   | category                                                                       |
| Data Layer Vers  | Version 2                                                                      |


| Field            | Value                                                                          |
|------------------|--------------------------------------------------------------------------------|
| Name:            | label                                                                          |
| Type:            | Data Layer Variable                                                            |
| Variable name:   | label                                                                          |
| Data Layer Vers  | Version 2                                                                      |

## Triggers

 To add the correct tags to all the appropriate pages, 4 GTM triggers must be defined as follows (the names are arbitrary).
 Note that the Drupal course page tag points Sailthru at the associated LMS course page to get it's interest tags.  The
 interest tags are loaded separately in to the Sailthru content library (through the Sailthru API)


| Field            | Value                                                                          |
|------------------|--------------------------------------------------------------------------------|
| Name:            | LMS Course Page                                                                |
| Event:           | Page View                                                                      |
| Trigger Type:    | DOM Ready                                                                      |
| Fire On:         | url contains courses.edx.org/courses/ & url ends with /info                    |


| Field            | Value                                                                          |
|------------------|--------------------------------------------------------------------------------|
| Name:            | Drupal Course Page                                                             |
| Event:           | Page View                                                                      |
| Trigger Type:    | DOM Ready                                                                      |
| Fire On:         | url contains edx.org/course/ & url does not contain edx.org/course/subject/    |


| Field            | Value                                                                          |
|------------------|--------------------------------------------------------------------------------|
| Name:            | Drupal Subject Page                                                            |
| Event:           | Page View                                                                      |
| Trigger Type:    | DOM Ready                                                                      |
| Fire On:         | url contains edx.org/course/subject/                                           |

 
| Field            | Value                                                                          |
|------------------|--------------------------------------------------------------------------------|
| Name:            | Drupal Other Page                                                              |
| Event:           | Page View                                                                      |
| Trigger Type:    | DOM Ready                                                                      |
| Fire On:         | url contains edx.org & url does not contain edx.org/course/                    |


| Field            | Value                                                                          |
|------------------|--------------------------------------------------------------------------------|
| Name:            | Course enroll                                                                  |
| Event:           | Custom event                                                                   |
| Trigger Type:    | n/a                                                                            |
| Fire On:         | url contains edx.org/course & event contains course-details.enroll             |


| Field            | Value                                                                          |
|------------------|--------------------------------------------------------------------------------|
| Name:            | Filtered course search                                                         |
| Event:           | Custom event                                                                   |
| Trigger Type:    | n/a                                                                            |
| Fire On:         | url ends with edx.org/course & event = edx.bi.user.*.filtered (regex)          |

##  Tags
 
 Two GTM tags are required

| Field            | Value                                                                          |
|------------------|--------------------------------------------------------------------------------|
| Name:            | Sailthru tagged page                                                           |
| Type:            | Custom HTML                                                                    |
| Firing Triggers: | LMS Course Page, Drupal Subject Page, Drupal Other Page                        |
| HTML:            | Copy from sailthru_standard.html                                               |


| Field            | Value                                                                          |
|------------------|--------------------------------------------------------------------------------|
| Name:            | Drupal course page tag                                                         |
| Type:            | Custom HTML                                                                    |
| Firing Triggers: | Drupal Course Page                                                             |
| HTML:            | Copy from sailthru_course.html                                                 |


| Field            | Value                                                                          |
|------------------|--------------------------------------------------------------------------------|
| Name:            | Sailthru filtered course search                                                |
| Type:            | Custom HTML                                                                    |
| Firing Triggers: | Course enroll                                                                  |
| HTML:            | Copy from sailthru_course_filters.html                                         |