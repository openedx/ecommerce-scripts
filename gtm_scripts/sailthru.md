
#  Instructions for configuring GTM for edX Sailthru integration

 These are configuration instructions for setting up GTM to capture activity for Sailthru at edX.  There is a change
 to template.php in edx_mktg to insert a meta field which provides the Sailthru interest tag information for most of the
 pages.  An example is:

  \<meta name="sailthru.tags" content="subject-economics-finance" /\>
 
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
